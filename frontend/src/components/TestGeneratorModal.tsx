"use client";
import { useState } from "react";
import { TestTube2, Download, Copy, CheckCheck, RefreshCw, X, ChevronRight, Sparkles } from "lucide-react";

interface TestSuiteItem {
  filename: string;
  source_file: string;
  test_code: string;
  functions_covered: string[];
  coverage_estimate: string;
}

interface GenerateTestsResponse {
  review_id: string;
  suites: TestSuiteItem[];
  total_suites: number;
  message: string;
}

interface TestGeneratorModalProps {
  reviewId: string;
  prNumber: number;
  onClose: () => void;
}

export function TestGeneratorModal({ reviewId, prNumber, onClose }: TestGeneratorModalProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateTestsResponse | null>(null);
  const [selectedSuite, setSelectedSuite] = useState<number>(0);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/reviews/${reviewId}/generate-tests`, { method: "POST" });
      if (!res.ok) throw new Error("Test generation failed");
      const data = await res.json();
      setResult(data);
      setSelectedSuite(0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const copyCode = () => {
    if (!result) return;
    navigator.clipboard.writeText(result.suites[selectedSuite]?.test_code || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadSuite = () => {
    if (!result) return;
    const suite = result.suites[selectedSuite];
    if (!suite) return;
    const blob = new Blob([suite.test_code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = suite.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const currentSuite = result?.suites[selectedSuite];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-3xl shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-700">
          <div className="flex items-center gap-2.5">
            <TestTube2 size={18} className="text-green-400" />
            <div>
              <div className="text-sm font-bold text-gray-100">AI Test Generator</div>
              <div className="text-xs text-gray-500">PR #{prNumber}</div>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col">
          {!result ? (
            <div className="flex flex-col items-center justify-center py-16 gap-5">
              <div className="w-16 h-16 rounded-2xl bg-green-900/30 border border-green-800 flex items-center justify-center">
                <TestTube2 size={32} className="text-green-400" />
              </div>
              <div className="text-center max-w-sm">
                <p className="text-gray-200 font-semibold text-base">Generate pytest Test Suites</p>
                <p className="text-gray-500 text-sm mt-2 leading-relaxed">
                  Gemini 2.5 will analyze modified functions and generate complete runnable pytest files
                  with fixtures, mocks, boundary cases, and edge-case parameterization.
                </p>
              </div>
              {error && (
                <div className="px-4 py-2 bg-red-900/30 border border-red-700 rounded-lg text-sm text-red-400">
                  {error}
                </div>
              )}
              <button
                onClick={generate}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-3 bg-green-700 hover:bg-green-600 disabled:opacity-50 rounded-xl text-sm font-bold text-white transition-colors shadow-lg shadow-green-900/30"
              >
                {loading ? <RefreshCw size={16} className="animate-spin" /> : <Sparkles size={16} />}
                {loading ? "Generating Tests..." : "Generate Test Suites"}
              </button>
            </div>
          ) : (
            <div className="flex flex-1 overflow-hidden">
              {/* Suite Sidebar */}
              <div className="w-48 border-r border-gray-700 overflow-y-auto bg-gray-800/30 flex-shrink-0">
                <div className="p-3 border-b border-gray-700">
                  <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    {result.total_suites} Suite{result.total_suites !== 1 ? "s" : ""}
                  </div>
                </div>
                {result.suites.map((suite, i) => (
                  <button
                    key={suite.filename}
                    onClick={() => setSelectedSuite(i)}
                    className={`w-full text-left p-3 border-b border-gray-800 transition-colors ${
                      selectedSuite === i
                        ? "bg-green-900/30 border-l-2 border-l-green-500"
                        : "hover:bg-gray-700/30"
                    }`}
                  >
                    <div className="text-xs font-mono text-gray-300 truncate">{suite.filename}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{suite.coverage_estimate}</div>
                  </button>
                ))}
              </div>

              {/* Code Pane */}
              <div className="flex-1 flex flex-col overflow-hidden">
                {currentSuite && (
                  <>
                    {/* Suite Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/30">
                      <div>
                        <div className="text-xs font-mono text-green-400">{currentSuite.filename}</div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          Source: {currentSuite.source_file} · {currentSuite.coverage_estimate}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {currentSuite.functions_covered.length > 0 && (
                          <div className="flex gap-1 flex-wrap">
                            {currentSuite.functions_covered.slice(0, 3).map((fn) => (
                              <span key={fn} className="px-1.5 py-0.5 bg-gray-700 rounded text-xs font-mono text-gray-300">
                                {fn}()
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Code */}
                    <div className="flex-1 overflow-y-auto">
                      <pre className="p-4 text-xs font-mono text-gray-300 leading-relaxed whitespace-pre-wrap">
                        {currentSuite.test_code}
                      </pre>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {result && (
          <div className="flex items-center justify-between px-5 py-4 border-t border-gray-700 bg-gray-800/30">
            <div className="text-xs text-gray-500">{result.message}</div>
            <div className="flex items-center gap-2">
              <button
                onClick={copyCode}
                className="flex items-center gap-1.5 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs font-medium text-gray-300 transition-colors"
              >
                {copied ? <CheckCheck size={13} className="text-green-400" /> : <Copy size={13} />}
                {copied ? "Copied" : "Copy"}
              </button>
              <button
                onClick={downloadSuite}
                className="flex items-center gap-1.5 px-3 py-2 bg-green-700 hover:bg-green-600 rounded-lg text-xs font-semibold text-white transition-colors"
              >
                <Download size={13} />
                Download .py
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
