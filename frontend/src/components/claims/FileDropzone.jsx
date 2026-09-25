import { useRef, useState } from "react";

import {
  FileText,
  Image,
  UploadCloud,
  X,
} from "lucide-react";

const ACCEPTED_EXTENSIONS = [
  ".txt",
  ".pdf",
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
];

function FileDropzone({ files, onFilesChange, disabled = false }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  function getExtension(filename) {
    const dotIndex = filename.lastIndexOf(".");

    if (dotIndex === -1) {
      return "";
    }

    return filename.slice(dotIndex).toLowerCase();
  }

  function isSupported(file) {
    return ACCEPTED_EXTENSIONS.includes(
      getExtension(file.name)
    );
  }

  function addFiles(fileList) {
    const incomingFiles = Array.from(fileList).filter(isSupported);

    const existingKeys = new Set(
      files.map((file) => `${file.name}-${file.size}`)
    );

    const uniqueFiles = incomingFiles.filter(
      (file) =>
        !existingKeys.has(`${file.name}-${file.size}`)
    );

    onFilesChange([...files, ...uniqueFiles]);
  }

  function handleInputChange(event) {
    addFiles(event.target.files);

    event.target.value = "";
  }

  function handleDrop(event) {
    event.preventDefault();

    if (disabled) {
      return;
    }

    setIsDragging(false);

    addFiles(event.dataTransfer.files);
  }

  function handleDragOver(event) {
    event.preventDefault();

    if (!disabled) {
      setIsDragging(true);
    }
  }

  function handleDragLeave(event) {
    event.preventDefault();

    setIsDragging(false);
  }

  function removeFile(indexToRemove) {
    onFilesChange(
      files.filter((_, index) => index !== indexToRemove)
    );
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) {
      return `${bytes} B`;
    }

    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function isImageFile(file) {
    return file.type.startsWith("image/");
  }

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={[
          "rounded-2xl border-2 border-dashed p-10 text-center transition",
          isDragging
            ? "border-indigo-500 bg-indigo-50"
            : "border-slate-300 bg-white",
          disabled
            ? "cursor-not-allowed opacity-60"
            : "cursor-pointer hover:border-indigo-400 hover:bg-slate-50",
        ].join(" ")}
        onClick={() => {
          if (!disabled) {
            inputRef.current?.click();
          }
        }}
      >
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
          <UploadCloud size={28} />
        </div>

        <h3 className="mt-5 text-base font-semibold text-slate-900">
          Upload claim evidence
        </h3>

        <p className="mt-2 text-sm text-slate-500">
          Drag and drop your claim files here, or click to browse.
        </p>

        <p className="mt-3 text-xs text-slate-400">
          TXT, PDF, JPG, JPEG, PNG and WEBP
        </p>

        <input
          ref={inputRef}
          type="file"
          multiple
          disabled={disabled}
          accept=".txt,.pdf,.jpg,.jpeg,.png,.webp"
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      {files.length > 0 && (
        <div className="mt-6 space-y-3">
          {files.map((file, index) => {
            const ImageOrFileIcon = isImageFile(file)
              ? Image
              : FileText;

            return (
              <div
                key={`${file.name}-${file.size}-${index}`}
                className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
                    <ImageOrFileIcon size={19} />
                  </div>

                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {file.name}
                    </p>

                    <p className="text-xs text-slate-500">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  disabled={disabled}
                  onClick={(event) => {
                    event.stopPropagation();
                    removeFile(index);
                  }}
                  className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed"
                  aria-label={`Remove ${file.name}`}
                >
                  <X size={18} />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default FileDropzone;