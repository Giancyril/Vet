"use client";
import { useState, useEffect } from "react";
import { ShieldCheck, Plus, Trash2, Play, CheckCircle2, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

interface PolicyRule {
  id: string;
  name: string;
  description: string;
  type: "regex" | "ast";
  pattern?: string;
  check?: string;
  severity: "error" | "warning" | "info";
  exclude_patterns?: string[];
}

interface BuiltinTemplate {
  id: string;
  name: string;
  description: string;
  severity: string;
}

interface PolicyEngineManagerProps {
  repoId: string;
}

const SEVERITY_COLORS = {
  error: "text-red-400 bg-red-900/30 border-red-700",
  warning: "text-yellow-400 bg-yellow-900/30 border-yellow-700",
  info: "text-blue-400 bg-blue-900/30 border-blue-700",
};

export function PolicyEngineManager({ repoId }: PolicyEngineManagerProps) {
  const [templates, setTemplates] = useState<BuiltinTemplate[]>([]);
  const [enabledBuiltins, setEnabledBuiltins] = useState<string[]>([]);
  const [customRules, setCustomRules] = useState<PolicyRule[]>([]);
  const [testSnippet, setTestSnippet] = useState("");
  const [testResults, setTestResults] = useState<unknown[]>([]);
  const [testPassed, setTestPassed] = useState<boolean | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [addingRule, setAddingRule] = useState(false);
  const [newRule, setNewRule] = useState<Partial<PolicyRule>>({
    type: "regex", severity: "warning",
  });

  useEffect(() => {
    fetch("/api/policy/templates").then(r => r.json()).then(d => setTemplates(d.templates || []));
    fetch(`/api/repos/${repoId}/policy`).then(r => r.json()).then(d => {
      setEnabledBuiltins(d.enabled_builtins || []);
      setCustomRules(d.custom_rules || []);
    });
  }, [repoId]);

  const toggleBuiltin = (id: string) => {
    setEnabledBuiltins(prev =>
      prev.includes(id) ? prev.filter(b => b !== id) : [...prev, id]
    );
  };

  const addCustomRule = () => {
    if (!newRule.id || !newRule.name) return;
    setCustomRules(prev => [...prev, newRule as PolicyRule]);
    setNewRule({ type: "regex", severity: "warning" });
    setAddingRule(false);
  };

  const removeCustomRule = (id: string) => {
    setCustomRules(prev => prev.filter(r => r.id !== id));
  };

  const savePolicy = async () => {
    setSaving(true);
    try {
      await fetch(`/api/repos/${repoId}/policy`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled_builtins: enabledBuiltins, custom_rules: customRules }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  const testFirstCustomRule = async () => {
    if (!customRules[0] || !testSnippet) return;
    setTesting(true);
    try {
      const res = await fetch("/api/policy/test-rule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rule: customRules[0], code_snippet: testSnippet }),
      });
      const data = await res.json();
      setTestResults(data.violations || []);
      setTestPassed(data.passed);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Built-in Templates */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-blue-400" />
            <span className="text-sm font-semibold text-gray-100">Built-in Policy Rules</span>
          </div>
          <span className="text-xs text-blue-400 font-mono">{enabledBuiltins.length}/{templates.length} enabled</span>
        </div>
        <div className="divide-y divide-gray-800">
          {templates.map((tpl) => (
            <div key={tpl.id} className="flex items-start gap-3 px-4 py-3">
              <input
                type="checkbox"
                checked={enabledBuiltins.includes(tpl.id)}
                onChange={() => toggleBuiltin(tpl.id)}
                className="mt-0.5 rounded border-gray-600 bg-gray-700 text-blue-500 cursor-pointer"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-200">{tpl.name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${SEVERITY_COLORS[tpl.severity as keyof typeof SEVERITY_COLORS] || SEVERITY_COLORS.info}`}>
                    {tpl.severity}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{tpl.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Custom Rules */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
          <span className="text-sm font-semibold text-gray-100">Custom Rules ({customRules.length})</span>
          <button
            onClick={() => setAddingRule(true)}
            className="flex items-center gap-1 px-3 py-1 bg-blue-700 hover:bg-blue-600 rounded-lg text-xs font-medium text-white transition-colors"
          >
            <Plus size={13} /> Add Rule
          </button>
        </div>

        {customRules.length === 0 && !addingRule ? (
          <div className="px-4 py-8 text-center text-sm text-gray-600 italic">
            No custom rules defined. Click "Add Rule" to create one.
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {customRules.map((rule) => (
              <div key={rule.id} className="flex items-start gap-3 px-4 py-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-200">{rule.name}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded border ${SEVERITY_COLORS[rule.severity]}`}>
                      {rule.severity}
                    </span>
                    <span className="text-xs px-1.5 py-0.5 rounded border border-gray-600 text-gray-500">{rule.type}</span>
                  </div>
                  {rule.pattern && (
                    <code className="text-xs text-purple-300 font-mono mt-0.5 block">{rule.pattern}</code>
                  )}
                </div>
                <button
                  onClick={() => removeCustomRule(rule.id)}
                  className="text-gray-600 hover:text-red-400 transition-colors mt-0.5"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {addingRule && (
          <div className="border-t border-gray-700 p-4 bg-gray-800/30 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input
                className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500"
                placeholder="Rule ID (e.g. no_todos)"
                value={newRule.id || ""}
                onChange={e => setNewRule(p => ({ ...p, id: e.target.value }))}
              />
              <input
                className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500"
                placeholder="Rule Name"
                value={newRule.name || ""}
                onChange={e => setNewRule(p => ({ ...p, name: e.target.value }))}
              />
            </div>
            <input
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm font-mono text-purple-300 placeholder-gray-600 focus:outline-none focus:border-blue-500"
              placeholder="Regex pattern (e.g. ^\+.*\bTODO\b)"
              value={newRule.pattern || ""}
              onChange={e => setNewRule(p => ({ ...p, pattern: e.target.value }))}
            />
            <div className="flex items-center gap-3">
              <select
                className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none"
                value={newRule.severity}
                onChange={e => setNewRule(p => ({ ...p, severity: e.target.value as PolicyRule["severity"] }))}
              >
                <option value="error">error</option>
                <option value="warning">warning</option>
                <option value="info">info</option>
              </select>
              <button
                onClick={addCustomRule}
                className="px-4 py-2 bg-blue-700 hover:bg-blue-600 rounded-lg text-xs font-semibold text-white transition-colors"
              >
                Add
              </button>
              <button
                onClick={() => setAddingRule(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs text-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Rule Tester */}
      {customRules.length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-700 bg-gray-800/50">
            <Play size={15} className="text-yellow-400" />
            <span className="text-sm font-semibold text-gray-100">Rule Tester</span>
            <span className="text-xs text-gray-500">(tests first custom rule)</span>
          </div>
          <div className="p-4 space-y-3">
            <textarea
              className="w-full h-28 bg-black/40 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-500 resize-none"
              placeholder="Paste code snippet to test against your first custom rule..."
              value={testSnippet}
              onChange={e => setTestSnippet(e.target.value)}
            />
            <button
              onClick={testFirstCustomRule}
              disabled={testing || !testSnippet}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-700 hover:bg-yellow-600 disabled:opacity-40 rounded-lg text-xs font-semibold text-white transition-colors"
            >
              <Play size={13} />
              {testing ? "Testing..." : "Run Test"}
            </button>
            {testPassed !== null && (
              <div className={`flex items-center gap-2 text-sm font-medium ${testPassed ? "text-green-400" : "text-red-400"}`}>
                {testPassed
                  ? <><CheckCircle2 size={16} /> Rule passed — no violations found</>
                  : <><AlertTriangle size={16} /> {(testResults as unknown[]).length} violation(s) found</>
                }
              </div>
            )}
            {(testResults as unknown[]).length > 0 && (
              <div className="space-y-1">
                {(testResults as Array<Record<string, unknown>>).map((v, i) => (
                  <div key={i} className="px-3 py-2 bg-red-900/20 border border-red-800 rounded text-xs text-red-300">
                    Line {String(v.line)}: {String(v.message)}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={savePolicy}
          disabled={saving}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${
            saved
              ? "bg-green-700 text-white"
              : "bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white"
          }`}
        >
          <ShieldCheck size={15} />
          {saving ? "Saving..." : saved ? "Saved!" : "Save Policy Configuration"}
        </button>
      </div>
    </div>
  );
}
