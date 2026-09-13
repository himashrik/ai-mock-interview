import React, { useRef, useState } from "react";

export default function FileDropzone({ accept, onFile, label }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState(null);

  const handleFiles = (files) => {
    if (files && files[0]) {
      setFileName(files[0].name);
      onFile(files[0]);
    }
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        dragging ? "border-accent bg-accentSoft" : "border-border/15 hover:border-accent/50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <p className="text-sm text-slate">
        {fileName ? (
          <span className="text-ink font-medium">{fileName}</span>
        ) : (
          <>
            <span className="text-accent font-medium">{label || "Click to upload"}</span> or drag and drop
          </>
        )}
      </p>
      <p className="text-xs text-slate/70 mt-1">PDF or DOCX, up to 8MB</p>
    </div>
  );
}
