import { Music, Upload, X } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useUploadFile, useUploadMultipleFiles, useUploadProgress } from '../hooks/useUpload';
import { useUIStore } from '../store/useUIStore';
import { cn } from '../utils/cn';

interface FileUploadProps {
  className?: string;
  multiple?: boolean;
  maxFiles?: number;
  maxSize?: number; // in bytes
  disabled?: boolean;
}

export function FileUpload({
  className,
  multiple = false,
  maxFiles = multiple ? 10 : 1,
  maxSize = 50 * 1024 * 1024, // 50MB default
  disabled = false,
}: FileUploadProps) {
  const [rejectedFiles, setRejectedFiles] = useState<File[]>([]);
  const { simulateProgress } = useUploadProgress();
  const uploadFile = useUploadFile();
  const uploadMultipleFiles = useUploadMultipleFiles();
  const isUploading = useUIStore((state) => state.isUploading);
  const uploadProgress = useUIStore((state) => state.uploadProgress);
  const addNotification = useUIStore((state) => state.addNotification);

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: any[]) => {
      setRejectedFiles(fileRejections.map((rejection) => rejection.file));

      if (acceptedFiles.length === 0) return;

      // Start progress simulation
      const stopProgress = simulateProgress();

      if (acceptedFiles.length === 1) {
        // Single file upload
        uploadFile.mutate(acceptedFiles[0], {
          onSuccess: () => {
            stopProgress();
          },
          onError: () => {
            stopProgress();
          },
        });
      } else {
        // Multiple file upload
        uploadMultipleFiles.mutate(acceptedFiles, {
          onSuccess: () => {
            stopProgress();
          },
          onError: () => {
            stopProgress();
          },
        });
      }
    },
    [uploadFile, uploadMultipleFiles, simulateProgress]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/mpeg': ['.mp3'],
      'audio/mp3': ['.mp3'],
    },
    multiple,
    maxFiles,
    maxSize,
    disabled: disabled || isUploading,
  });

  const removeRejectedFile = (file: File) => {
    setRejectedFiles((prev) => prev.filter((f) => f !== file));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={cn('w-full', className)}>
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          'hover:border-blue-400 hover:bg-blue-50 dark:hover:border-blue-600 dark:hover:bg-blue-950',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          isDragActive && 'border-blue-500 bg-blue-50 dark:bg-blue-950',
          (disabled || isUploading) && 'opacity-50 cursor-not-allowed',
          'border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-900'
        )}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center space-y-4">
          <div className="p-4 bg-blue-100 dark:bg-blue-900 rounded-full">
            {isUploading ? (
              <div className="animate-spin">
                <Upload className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              </div>
            ) : (
              <Music className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            )}
          </div>
          
          <div className="space-y-2">
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {isDragActive
                ? 'Drop the audio files here...'
                : isUploading
                ? 'Uploading...'
                : 'Drop MP3 files here or click to browse'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {multiple
                ? `Upload up to ${maxFiles} files`
                : 'Upload a single file'} • Max {formatFileSize(maxSize)} each
            </p>
          </div>

          {isUploading && (
            <div className="w-full max-w-md">
              <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                {uploadProgress}% uploaded
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Rejected files */}
      {rejectedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <p className="text-sm font-medium text-red-600 dark:text-red-400">
            The following files were rejected:
          </p>
          {rejectedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
            >
              <div className="flex items-center space-x-3">
                <Music className="h-5 w-5 text-red-600 dark:text-red-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>
              <button
                onClick={() => removeRejectedFile(file)}
                className="p-1 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Upload status messages */}
      {uploadFile.error && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">
            Upload failed: {(uploadFile.error as any)?.message}
          </p>
        </div>
      )}

      {uploadFile.isSuccess && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <p className="text-sm text-green-600 dark:text-green-400">
            File uploaded successfully!
          </p>
        </div>
      )}
    </div>
  );
}