import React, { useState, useRef } from 'react';
import {
  X,
  UploadCloud,
  FileArchive,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Share2,
  Box,
  FileCode
} from 'lucide-react';
import { api } from '../../api/client';
import { UploadResponse } from '../../types/graph';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (response: UploadResponse) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [repoName, setRepoName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (selected: File | null) => {
    if (!selected) return;
    if (!selected.name.toLowerCase().endsWith('.zip')) {
      setError('Please select a valid .zip repository archive');
      return;
    }
    setError(null);
    setFile(selected);
    if (!repoName) {
      setRepoName(selected.name.replace(/\.zip$/i, ''));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !repoName.trim()) {
      setError('Both a ZIP archive and repository name are required');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const result = await api.uploadRepository(file, repoName.trim());
      setUploadResult(result);
      onUploadSuccess(result);
    } catch (err: any) {
      setError(err.message || 'Ingestion failed');
    } finally {
      setUploading(false);
    }
  };

  const resetModal = () => {
    setFile(null);
    setRepoName('');
    setError(null);
    setUploadResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-midnight-950/80 backdrop-blur-md">
      <div className="w-full max-w-lg bg-midnight-900 border border-midnight-700 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="p-5 border-b border-midnight-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center">
              <UploadCloud className="w-4 h-4 text-cyber-cyan" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white font-mono">Ingest Python Repository</h3>
              <p className="text-[11px] text-slate-400 font-mono">AST static analysis & real Neo4j persistence</p>
            </div>
          </div>
          <button
            onClick={resetModal}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-midnight-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {uploadResult ? (
          /* Ingestion Result Summary Screen */
          <div className="p-6 space-y-5">
            <div className="flex items-center gap-3 p-4 bg-cyber-emerald/10 border border-cyber-emerald/30 rounded-xl">
              <CheckCircle2 className="w-6 h-6 text-cyber-emerald flex-shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-white font-mono">Repository Successfully Ingested</h4>
                <p className="text-xs text-slate-300 font-mono">Persisted into Neo4j graph database</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-midnight-950 border border-midnight-800 p-2.5 rounded-lg flex items-center gap-2">
                <FileCode className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-slate-500 text-[10px] block">Files Parsed</span>
                  <span className="text-white font-bold">{uploadResult.files_parsed}</span>
                </div>
              </div>
              <div className="bg-midnight-950 border border-midnight-800 p-2.5 rounded-lg flex items-center gap-2">
                <Box className="w-4 h-4 text-sky-400" />
                <div>
                  <span className="text-slate-500 text-[10px] block">Modules</span>
                  <span className="text-sky-400 font-bold">{uploadResult.modules_found}</span>
                </div>
              </div>
              <div className="bg-midnight-950 border border-midnight-800 p-2.5 rounded-lg flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyber-violet" />
                <div>
                  <span className="text-slate-500 text-[10px] block">Classes</span>
                  <span className="text-cyber-violet font-bold">{uploadResult.classes_found}</span>
                </div>
              </div>
              <div className="bg-midnight-950 border border-midnight-800 p-2.5 rounded-lg flex items-center gap-2">
                <Share2 className="w-4 h-4 text-cyber-emerald" />
                <div>
                  <span className="text-slate-500 text-[10px] block">Functions & Methods</span>
                  <span className="text-cyber-emerald font-bold">{uploadResult.functions_found}</span>
                </div>
              </div>
            </div>

            <div className="p-3 bg-midnight-950 border border-midnight-800 rounded-lg flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Static Function Calls Inferred:</span>
              <span className="text-cyber-cyan font-bold">{uploadResult.calls_inferred}</span>
            </div>

            {uploadResult.warnings.length > 0 && (
              <div className="p-3 bg-cyber-amber/10 border border-cyber-amber/30 rounded-lg space-y-1">
                <div className="flex items-center gap-1.5 text-cyber-amber text-xs font-mono font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Syntax Warnings ({uploadResult.warnings.length})</span>
                </div>
                <div className="max-h-24 overflow-y-auto text-[11px] font-mono text-slate-300 space-y-1">
                  {uploadResult.warnings.map((w, idx) => (
                    <div key={idx} className="truncate">• {w}</div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={resetModal}
              className="w-full flex items-center justify-center gap-2 bg-cyber-cyan hover:bg-cyber-cyan/90 text-midnight-950 text-xs font-bold font-mono py-2.5 rounded-xl transition-all shadow-glow-cyan"
            >
              <span>Explore Graph Architecture</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          /* Upload Form */
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="p-3 bg-cyber-rose/10 border border-cyber-rose/30 rounded-xl text-cyber-rose text-xs font-mono flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Drag & Drop Zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
                file
                  ? 'border-cyber-cyan/50 bg-cyber-cyan/5'
                  : 'border-midnight-700 hover:border-midnight-600 bg-midnight-950/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
              />

              {file ? (
                <div className="space-y-2">
                  <FileArchive className="w-10 h-10 text-cyber-cyan mx-auto" />
                  <div className="text-xs font-mono text-white font-semibold truncate max-w-xs mx-auto">
                    {file.name}
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <UploadCloud className="w-10 h-10 text-slate-500 mx-auto" />
                  <div className="text-xs font-mono text-slate-300">
                    <span className="text-cyber-cyan font-semibold">Click to browse</span> or drag & drop ZIP
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Max size 25MB • Pure AST parsing (zero code execution)
                  </div>
                </div>
              )}
            </div>

            {/* Repository Name Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-slate-300 block">Repository Label</label>
              <input
                type="text"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                placeholder="e.g. sample_ecommerce_api"
                required
                className="w-full bg-midnight-950 border border-midnight-700 focus:border-cyber-cyan rounded-xl px-3.5 py-2 text-xs font-mono text-white placeholder:text-slate-600 focus:outline-none transition-colors"
              />
            </div>

            {/* Security Guarantee Notice */}
            <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 pt-1">
              <ShieldCheck className="w-4 h-4 text-cyber-emerald flex-shrink-0" />
              <span>Zip-Slip protected • Sanitized sandbox AST evaluation</span>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={uploading || !file}
              className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-mono font-bold transition-all ${
                uploading || !file
                  ? 'bg-midnight-800 text-slate-500 cursor-not-allowed'
                  : 'bg-cyber-cyan hover:bg-cyber-cyan/90 text-midnight-950 shadow-glow-cyan active:scale-98'
              }`}
            >
              {uploading ? (
                <>
                  <div className="w-4 h-4 border-2 border-midnight-950 border-t-transparent rounded-full animate-spin" />
                  <span>Parsing AST & Persisting to Neo4j...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Begin Ingestion & Analysis</span>
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
