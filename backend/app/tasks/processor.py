import asyncio
from typing import Dict, List

import librosa
import music21
import numpy as np
from loguru import logger

from ..config import get_settings
from ..utils.file_handler import get_file_handler
from ..utils.logging import log_async_performance


class AudioProcessor:
    """Audio processing pipeline for MP3 to MIDI conversion"""

    def __init__(self):
        self.settings = get_settings()
        self.file_handler = get_file_handler()

    @log_async_performance
    async def load_audio(self, file_path: str) -> np.ndarray:
        """
        Load and preprocess audio file

        Args:
            file_path: Path to MP3 file

        Returns:
            Audio data as numpy array

        Raises:
            Exception: If audio loading fails
        """
        try:
            # Load audio file in a thread to avoid blocking
            audio_data, sample_rate = await asyncio.to_thread(
                librosa.load,
                file_path,
                sr=self.settings.sample_rate,
                mono=True,  # Convert to mono
                duration=None,  # Load entire file
            )

            logger.info(
                f"Audio loaded: {file_path}, shape: {tuple(audio_data.shape)}, sr: {sample_rate}"
            )

            # Validate audio quality
            if len(audio_data) == 0:
                raise ValueError("Audio file is empty or corrupted")

            # Check duration
            duration = len(audio_data) / sample_rate
            if duration < self.settings.min_duration:
                raise ValueError(f"Audio duration ({duration:.2f}s) is too short")
            if duration > self.settings.max_duration:
                raise ValueError(f"Audio duration ({duration:.2f}s) is too long")

            return audio_data

        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {e}")
            raise

    @log_async_performance
    async def extract_features(self, audio_data: np.ndarray) -> Dict:
        """
        Extract audio features

        Args:
            audio_data: Audio data as numpy array

        Returns:
            Dictionary of extracted features
        """
        try:
            features = {}

            # Extract tempo
            tempo, beats = await asyncio.to_thread(
                librosa.beat.beat_track,
                y=audio_data,
                sr=self.settings.sample_rate,
                hop_length=self.settings.hop_length,
            )
            features["tempo"] = float(tempo)
            features["beats"] = beats.tolist()

            # Extract chroma features (harmonic content)
            chroma = await asyncio.to_thread(
                librosa.feature.chroma_cqt,
                y=audio_data,
                sr=self.settings.sample_rate,
                hop_length=self.settings.hop_length,
            )
            features["chroma"] = chroma.tolist()

            # Extract MFCC features (timbral content)
            mfcc = await asyncio.to_thread(
                librosa.feature.mfcc,
                y=audio_data,
                sr=self.settings.sample_rate,
                n_mfcc=13,
                hop_length=self.settings.hop_length,
            )
            features["mfcc"] = mfcc.tolist()

            # Extract spectral centroid (brightness)
            spectral_centroids = await asyncio.to_thread(
                librosa.feature.spectral_centroid,
                y=audio_data,
                sr=self.settings.sample_rate,
                hop_length=self.settings.hop_length,
            )
            features["spectral_centroid"] = spectral_centroids.tolist()

            # Extract onset detection (note start times)
            onset_frames = await asyncio.to_thread(
                librosa.onset.onset_detect,
                y=audio_data,
                sr=self.settings.sample_rate,
                hop_length=self.settings.hop_length,
            )
            onset_times = librosa.frames_to_time(
                onset_frames,
                sr=self.settings.sample_rate,
                hop_length=self.settings.hop_length,
            )
            features["onsets"] = onset_times.tolist()

            # Extract key signature
            key = await self._detect_key(audio_data)
            features["key"] = key

            # Calculate duration
            duration = len(audio_data) / self.settings.sample_rate
            features["duration"] = duration

            logger.info(
                f"Features extracted: tempo={float(tempo):.1f}, key={key}, duration={float(duration):.2f}s"
            )

            return features

        except Exception as e:
            logger.error(f"Failed to extract features: {e}")
            raise

    async def _detect_key(self, audio_data: np.ndarray) -> str:
        """
        Detect musical key from audio

        Args:
            audio_data: Audio data as numpy array

        Returns:
            Detected key as string (e.g., "C major")
        """
        try:
            # Extract chroma features
            chroma = await asyncio.to_thread(
                librosa.feature.chroma_cqt,
                y=audio_data,
                sr=self.settings.sample_rate,
                hop_length=self.settings.hop_length,
            )

            # Average chroma over time
            chroma_mean = np.mean(chroma, axis=1)

            # Find the most prominent pitch class
            max_idx = np.argmax(chroma_mean)

            # Map to key names (simplified)
            pitch_classes = [
                "C",
                "C#",
                "D",
                "D#",
                "E",
                "F",
                "F#",
                "G",
                "G#",
                "A",
                "A#",
                "B",
            ]
            major_minor = self._detect_major_minor(chroma_mean)

            key = f"{pitch_classes[max_idx]} {major_minor}"
            return key

        except Exception as e:
            logger.warning(f"Failed to detect key: {e}")
            return "C major"  # Default

    def _detect_major_minor(self, chroma_mean: np.ndarray) -> str:
        """
        Simple major/minor detection based on chroma patterns

        Args:
            chroma_mean: Mean chroma values

        Returns:
            "major" or "minor"
        """
        # Simplified major/minor detection
        # Major keys typically have strong 3rd and 5th
        # Minor keys typically have strong minor 3rd
        major_strength = (
            chroma_mean[4] + chroma_mean[7]
        )  # E and B (major 3rd and 5th from C)
        minor_strength = (
            chroma_mean[3] + chroma_mean[7]
        )  # Eb and B (minor 3rd and 5th from C)

        return "major" if major_strength > minor_strength else "minor"

    @log_async_performance
    async def detect_pitches(
        self, audio_data: np.ndarray, features: Dict
    ) -> List[Dict]:
        """
        Detect pitches and create note events

        Args:
            audio_data: Audio data as numpy array
            features: Extracted audio features

        Returns:
            List of note events with timing and pitch information
        """
        try:
            notes = []

            # Use onset times from features
            onsets = features.get("onsets", [])

            # Extract pitch using YIN algorithm
            pitches, magnitudes = await asyncio.to_thread(
                librosa.piptrack,
                y=audio_data,
                sr=self.settings.sample_rate,
                threshold=0.1,
                fmin=librosa.note_to_hz("C2"),
                fmax=librosa.note_to_hz("C7"),
            )

            # Convert onset times to frame indices
            onset_frames = librosa.time_to_frames(
                onsets,
                sr=self.settings.sample_rate,
                hop_length=self.settings.hop_length,
            )

            # Extract notes at each onset
            for i, onset_frame in enumerate(onset_frames):
                if onset_frame < len(pitches[0]):
                    # Get pitch at this onset
                    frame_pitches = pitches[:, onset_frame]
                    frame_mags = magnitudes[:, onset_frame]

                    # Find the most prominent pitch
                    valid_pitches = frame_pitches[frame_mags > 0.1]  # Threshold
                    if len(valid_pitches) > 0:
                        # Use median pitch for stability
                        pitch_hz = np.median(valid_pitches)

                        if pitch_hz > 0:  # Valid pitch
                            # Convert to MIDI note number
                            midi_note = librosa.hz_to_midi(pitch_hz)

                            # Calculate note duration
                            if i < len(onsets) - 1:
                                duration = onsets[i + 1] - onsets[i]
                            else:
                                duration = features["duration"] - onsets[i]

                            # Create note event
                            note = {
                                "midi_note": int(round(midi_note)),
                                "frequency": float(pitch_hz),
                                "start_time": float(onsets[i]),
                                "duration": float(duration),
                                "velocity": 80,  # Default velocity
                                "confidence": float(np.max(frame_mags))
                                if len(frame_mags) > 0
                                else 0.0,
                            }

                            notes.append(note)

            logger.info(f"Detected {len(notes)} notes")
            return notes

        except Exception as e:
            logger.error(f"Failed to detect pitches: {e}")
            raise

    @log_async_performance
    async def generate_midi(self, notes: List[Dict], features: Dict) -> bytes:
        """
        Generate MIDI file from detected notes

        Args:
            notes: List of note events
            features: Audio features for tempo and key

        Returns:
            MIDI file content as bytes
        """
        try:
            # Create music21 stream
            stream = music21.stream.Stream()

            # Initialize and add metadata
            stream.metadata = music21.metadata.Metadata(
                title="Audio2MidiFlow Conversion", composer="Audio2MidiFlow"
            )

            # Set tempo
            tempo = features.get("tempo", 120.0)
            stream.append(music21.tempo.MetronomeMark(number=tempo))

            # Create a part for the melody
            part = music21.stream.Part()
            part.id = "melody"

            # Add key signature
            key_str = features.get("key", "C major")
            key_signature = self._parse_key_signature(key_str)
            part.append(key_signature)

            # Add time signature
            part.append(music21.meter.TimeSignature(number=4, type=4))

            # Convert notes to music21 format
            for note_data in notes:
                # Create music21 note
                midi_note = note_data["midi_note"]
                duration = note_data["duration"]
                velocity = note_data["velocity"]

                # Convert duration to music21 duration
                duration_obj = self._duration_to_music21(duration, tempo)

                # Create note
                note = music21.note.Note(
                    pitch=midi_note, duration=duration_obj, velocity=velocity
                )

                # Set start time (offset)
                note.offset = note_data["start_time"]

                part.append(note)

            # Add part to stream
            stream.append(part)

            # Convert to MIDI bytes
            # First write to a temporary file, then read the bytes
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Write MIDI to file
            await asyncio.to_thread(stream.write, "midi", fp=tmp_path)

            # Read the file as bytes
            with open(tmp_path, "rb") as f:
                midi_bytes = f.read()

            # Clean up temporary file
            import os

            os.unlink(tmp_path)

            logger.info(f"MIDI generated: {len(notes)} notes, tempo={tempo}")
            return midi_bytes

        except Exception as e:
            logger.error(f"Failed to generate MIDI: {e}")
            raise

    def _parse_key_signature(self, key_str: str) -> music21.key.Key:
        """
        Parse key string to music21 Key object

        Args:
            key_str: Key string (e.g., "C major")

        Returns:
            music21 Key object
        """
        try:
            parts = key_str.split()
            if len(parts) == 2:
                tonic, mode = parts
                if mode.lower() == "major":
                    return music21.key.Key(tonic, "major")
                elif mode.lower() == "minor":
                    return music21.key.Key(tonic, "minor")

            # Default to C major
            return music21.key.Key("C", "major")

        except Exception as e:
            logger.warning(f"Failed to parse key signature '{key_str}': {e}")
            return music21.key.Key("C", "major")

    def _duration_to_music21(
        self, duration_seconds: float, tempo: float
    ) -> music21.duration.Duration:
        """
        Convert duration in seconds to music21 Duration object

        Args:
            duration_seconds: Duration in seconds
            tempo: Tempo in BPM

        Returns:
            music21 Duration object
        """
        try:
            # Calculate duration in quarter notes
            quarter_note_duration = 60.0 / tempo  # seconds per quarter note
            duration_quarters = duration_seconds / quarter_note_duration

            # Convert to music21 duration
            return music21.duration.Duration(quarterLength=duration_quarters)

        except Exception as e:
            logger.warning(f"Failed to convert duration {duration_seconds}: {e}")
            return music21.duration.Duration(
                quarterLength=1.0
            )  # Default to quarter note

    @log_async_performance
    async def validate_audio_quality(self, file_path: str) -> Dict:
        """
        Validate audio quality before processing

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with quality metrics
        """
        try:
            # Load audio
            audio_data, sample_rate = await asyncio.to_thread(
                librosa.load, file_path, sr=self.settings.sample_rate, mono=True
            )

            # Calculate quality metrics
            duration = len(audio_data) / sample_rate

            # RMS energy (loudness)
            rms = np.sqrt(np.mean(audio_data**2))

            # Peak amplitude
            peak = np.max(np.abs(audio_data))

            # Zero crossing rate (indicates noise)
            zcr = np.mean(librosa.feature.zero_crossing_rate(audio_data))

            # Spectral centroid (brightness)
            spectral_centroid = np.mean(
                librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)
            )

            quality_metrics = {
                "duration": duration,
                "rms_energy": float(rms),
                "peak_amplitude": float(peak),
                "zero_crossing_rate": float(zcr),
                "spectral_centroid": float(spectral_centroid),
                "sample_rate": sample_rate,
                "quality_score": self._calculate_quality_score(
                    duration, rms, zcr, spectral_centroid
                ),
            }

            logger.info(f"Audio quality metrics: {quality_metrics}")
            return quality_metrics

        except Exception as e:
            logger.error(f"Failed to validate audio quality: {e}")
            return {}

    def _calculate_quality_score(
        self, duration: float, rms: float, zcr: float, spectral_centroid: float
    ) -> float:
        """
        Calculate overall quality score

        Args:
            duration: Audio duration
            rms: RMS energy
            zcr: Zero crossing rate
            spectral_centroid: Spectral centroid

        Returns:
            Quality score between 0 and 1
        """
        score = 1.0

        # Duration penalty
        if duration < self.settings.min_duration:
            score *= 0.5
        elif duration > self.settings.max_duration:
            score *= 0.3

        # Energy penalty (too quiet)
        if rms < 0.01:
            score *= 0.7

        # Noise penalty (high zero crossing rate)
        if zcr > 0.1:
            score *= 0.8

        # Brightness penalty (very low spectral centroid might indicate poor quality)
        if spectral_centroid < 500:
            score *= 0.9

        return max(0.0, min(1.0, score))
