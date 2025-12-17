import { useEffect, useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PDFViewer } from "@/components/invoice/PDFViewer";
import { InvoiceDataEditor } from "@/components/invoice/InvoiceDataEditor";
import { useInvoice } from "@/context/InvoiceContext";
import { toast } from "sonner";
import { Invoice } from "@/types/invoice";
import {
  Loader2,
  PanelLeftClose,
  PanelLeftOpen,
  ExternalLink,
  CircleHelp,
  FileText,
} from "lucide-react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useHotkeys } from "react-hotkeys-hook";
import { KeyboardShortcutsDialog } from "@/components/ui/keyboard-shortcuts-dialog";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import { useLocalDraft } from "@/hooks/useLocalDraft";
import { useAuth } from "@/context/AuthContext";

export default function InvoiceReview() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getInvoice, updateInvoice, invoices, isLoading } = useInvoice();
  const { getToken } = useAuth();
  const [invoice, setInvoice] = useState<Invoice | undefined>(undefined);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [isPdfVisible, setIsPdfVisible] = useState(true);
  const { saveDraft, getDraft, clearDraft, hasDraft } = useLocalDraft();

  // Highlight State
  const [highlights, setHighlights] = useState<Record<string, any[]>>({});
  const [activeField, setActiveField] = useState<string | null>(null);
  const [validationWarnings, setValidationWarnings] = useState<{ global_warnings: string[], line_item_warnings: Record<string, string[]> }>({ global_warnings: [], line_item_warnings: {} });

  // Construct PDF URL once for use in viewer and popout
  const getPdfUrl = () => {
    if (!invoice?.fileUrl) return '';
    if (invoice.fileUrl.startsWith('http')) return invoice.fileUrl;
    const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';
    return `${API_BASE}${invoice.fileUrl}`;
  };

  const pdfUrl = getPdfUrl();
  const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';

  useEffect(() => {
    if (id) {
      const data = getInvoice(id);
      if (data) {
        setInvoice(data);

        // Fetch data with proper auth
        (async () => {
          try {
            const token = await getToken();

            // Fetch highlights
            fetch(`${API_BASE}/api/invoices/${id}/highlights`, {
              headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
            })
              .then(res => res.json())
              .then(data => setHighlights(data))
              .catch(err => console.error("Failed to load highlights", err));

            // Fetch Smart Validation
            fetch(`${API_BASE}/api/invoices/${id}/validate`, {
              headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
            })
              .then(res => res.json())
              .then(data => setValidationWarnings(data))
              .catch(err => console.error("Failed to load validation", err));

          } catch (err) {
            console.error("Auth error", err);
          }
        })();

        // Check for local draft
        if (hasDraft(id)) {
          const draft = getDraft(id);
          if (draft && draft.timestamp > new Date(data.updatedAt || 0).getTime()) {
            toast("Unsaved changes found", {
              description: "You have unsaved edits from a previous session.",
              action: {
                label: "Restore",
                onClick: () => {
                  setInvoice({ ...data, ...draft.data });
                  toast.success("Draft restored");
                }
              },
              duration: 8000,
            });
          }
        }
      } else {
        if (!isLoading) {
          toast.error("Invoice not found");
          navigate("/dashboard");
        }
      }
    }
  }, [id, getInvoice, navigate, hasDraft, getDraft, isLoading]);

  // Tour logic
  const tourStartedRef = useRef(false);

  useEffect(() => {
    // Only run if we haven't started yet and we have a valid invoice
    if (!tourStartedRef.current && invoice) {
      const hasSeenTour = localStorage.getItem('hasSeenTour');

      if (!hasSeenTour) {
        tourStartedRef.current = true; // Mark as started immediately

        // Create driver
        const driverObj = driver({
          showProgress: true,
          popoverClass: 'driverjs-theme',
          steps: [
            { element: '#pdf-panel', popover: { title: 'The Source', description: 'This is the original invoice PDF. You can zoom, pan, or pop it out.' } },
            { element: '#tour-data-panel', popover: { title: 'The Data (Truth Ray)', description: 'Here is the data extracted by AI. Click on any field (like Total Amount) to see a yellow box light up on the PDF showing exactly where it came from.' } },
            { element: '#tour-actions', popover: { title: 'Take Action', description: 'When you are happy with the data, approve it to move the invoice forward.' } }
          ],
          onDestroyStarted: () => {
            if (!driverObj.hasNextStep()) {
              driverObj.destroy();
              localStorage.setItem('hasSeenTour', 'true');
              return;
            }
            if (confirm("End the tour?")) {
              driverObj.destroy();
              localStorage.setItem('hasSeenTour', 'true');
            }
          },
        });

        // Delay slightly to ensure render
        setTimeout(() => driverObj.drive(), 1500);
      }
    }
  }, [invoice]); // Still depend on invoice, but gated by ref

  const handleDataChange = (updates: Partial<Invoice>) => {
    if (invoice) {
      // Update local state immediately for responsive UI
      const newData = { ...invoice, ...updates };
      setInvoice(newData);

      // Save local draft immediately
      saveDraft(invoice.id, updates);

      // Clear existing timeout
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      // Debounce the save - wait 1 second after user stops typing
      saveTimeoutRef.current = setTimeout(() => {
        updateInvoice(invoice.id, updates);
      }, 1000);
    }
  };

  const handleSave = () => {
    if (invoice && saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      updateInvoice(invoice.id, invoice); // Force immediate save
      toast.success("Changes saved");
    }
  };

  const handleApprove = async () => {
    if (!invoice) return;
    try {
      await updateInvoice(invoice.id, { status: 'approved' });
      toast.success("Invoice Approved", {
        description: "Moving to next invoice...",
        duration: 2000,
      });

      // Auto-navigate to next 'needs_review' invoice if possible
      const nextInvoice = invoices.find(i => i.status === 'needs_review' && i.id !== invoice.id);
      if (nextInvoice) {
        navigate(`/invoices/${nextInvoice.id}`);
      } else {
        navigate("/dashboard");
      }
    } catch (error) {
      console.error(error);
    }
  };

  const handleReject = () => {
    if (invoice) {
      updateInvoice(invoice.id, { status: 'failed' }); // Or some other status
      toast.info("Invoice marked as rejected");
      navigate("/dashboard");
    }
  };

  useHotkeys('meta+s, ctrl+s', (e) => {
    e.preventDefault();
    handleSave();
  }, { enableOnFormTags: true }, [invoice]);

  useHotkeys('meta+enter, ctrl+enter', (e) => {
    e.preventDefault();
    handleApprove();
  }, { enableOnFormTags: true }, [invoice, handleApprove]);

  useHotkeys('shift+?', () => setShowShortcuts(true));

  useHotkeys('j, right', () => {
    if (!invoice || invoices.length === 0) return;
    const currentIndex = invoices.findIndex(i => i.id === invoice.id);
    if (currentIndex < invoices.length - 1) {
      navigate(`/invoices/${invoices[currentIndex + 1].id}`);
    }
  }, [invoice, invoices, navigate]);

  useHotkeys('k, left', () => {
    if (!invoice || invoices.length === 0) return;
    const currentIndex = invoices.findIndex(i => i.id === invoice.id);
    if (currentIndex > 0) {
      navigate(`/invoices/${invoices[currentIndex - 1].id}`);
    }
  }, [invoice, invoices, navigate]);

  if (!invoice) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background-light font-display text-gray-800">
      <header className="flex-shrink-0 border-b border-gray-200 bg-background-light">
        <div className="mx-auto w-full px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <div className="flex items-center gap-2 text-xl font-bold">
                <div className="bg-primary p-1.5 rounded-lg flex items-center justify-center">
                  <FileText className="h-5 w-5 text-white" />
                </div>
                <span className="text-gray-900">InvoiceAI</span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              {!isPdfVisible && (
                <button
                  onClick={() => setIsPdfVisible(true)}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors"
                  title="Show PDF Panel"
                >
                  <PanelLeftOpen className="h-5 w-5" />
                  <span>Show PDF</span>
                </button>
              )}

              <button
                onClick={() => {
                  localStorage.removeItem('hasSeenTour');
                  window.location.reload();
                }}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg flex items-center text-sm font-medium transition-colors"
                title="Restart Product Tour"
              >
                <CircleHelp className="h-5 w-5" />
              </button>

              <button onClick={() => navigate("/dashboard")} className="px-4 py-2 text-sm font-medium border rounded-lg border-gray-300 text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary" type="button">
                Back
              </button>
              <button
                onClick={async () => {
                  const savedColumns = localStorage.getItem("csv_export_columns");
                  const savedConfig = localStorage.getItem("csv_export_config");

                  const API_BASE = import.meta.env.PROD ? 'https://invoice-backend-a1gb.onrender.com' : 'http://localhost:8000';
                  // Token is already awaited due to 'await' keyword but verify context
                  const token = await getToken();

                  let url = `${API_BASE}/api/invoices/${invoice.id}/export/csv`;

                  // Construct columns mapping
                  if (savedColumns) {
                    const enabledColumns = JSON.parse(savedColumns) as string[];
                    const configMap = savedConfig ? JSON.parse(savedConfig) : {};

                    // Create object: { "Internal Name": "Custom Header" }
                    const exportMap: Record<string, string> = {};
                    enabledColumns.forEach(col => {
                      exportMap[col] = configMap[col] || col;
                    });

                    url += `?columns=${encodeURIComponent(JSON.stringify(exportMap))}`;
                  }

                  try {
                    const response = await fetch(url, {
                      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
                    });

                    if (!response.ok) throw new Error('Export failed');

                    const blob = await response.blob();
                    const objectUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = objectUrl;
                    a.download = `invoice-${invoice.invoiceNumber || 'export'}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(objectUrl);
                    document.body.removeChild(a);

                    toast.success("CSV file has been downloaded", {
                      description: "Export Successful",
                    });
                  } catch (error) {
                    console.error('Export error:', error);
                    toast.error("Could not download CSV file", {
                      description: "Export Failed",
                    });
                  }
                }}
                className="px-4 py-2 text-sm font-medium border rounded-lg border-gray-300 text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary flex items-center gap-2"
                type="button"
              >
                <span className="material-symbols-outlined text-base">download</span>
                CSV
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-grow min-h-0">
        <ResizablePanelGroup direction="horizontal" className="h-full w-full rounded-lg border">
          {isPdfVisible && (
            <>
              <ResizablePanel defaultSize={50} minSize={30} id="tour-pdf-panel">
                <div className="relative h-full bg-gray-50 p-4 md:p-6 lg:p-8 flex flex-col" id="pdf-panel">
                  <div className="flex items-center justify-between pb-4">
                    <h2 className="text-lg font-semibold text-gray-900">Invoice Preview</h2>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => window.open(pdfUrl, '_blank', 'noopener,noreferrer')}
                        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-md transition-colors"
                        title="Open in new window"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setIsPdfVisible(false)}
                        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-md transition-colors"
                        title="Hide PDF Panel"
                      >
                        <PanelLeftClose className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div className="flex-grow bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden relative">
                    <PDFViewer
                      pdfUrl={pdfUrl}
                      highlights={activeField ? highlights[
                        // Convert camelCase to snake_case for lookup
                        activeField.replace(/lineItems\[(\d+)\]\.([a-zA-Z]+)/, (_, idx, field) =>
                          `line_items[${idx}].${field.replace(/[A-Z]/g, l => `_${l.toLowerCase()}`)}`
                        ).replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
                      ] || [] : []}
                    />
                  </div>
                </div>
              </ResizablePanel>
              <ResizableHandle withHandle />
            </>
          )}

          <ResizablePanel defaultSize={isPdfVisible ? 50 : 100} minSize={30}>
            <div className="flex-1 h-full p-4 md:p-6 lg:p-8 overflow-y-auto" id="tour-data-panel">
              <InvoiceDataEditor
                data={invoice}
                onChange={handleDataChange}
                onFieldFocus={(field) => setActiveField(field)}
                validation={validationWarnings}
              />

              <div className="pt-8 border-t border-gray-200 mt-8">
                <div className="flex justify-end gap-3" id="tour-actions">
                  <button onClick={handleReject} className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500" type="button">
                    <span className="material-symbols-outlined text-base -ml-1 mr-2">close</span>
                    <span>Reject</span>
                  </button>
                  <button onClick={handleApprove} className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-lg shadow-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500" type="button">
                    <span className="material-symbols-outlined text-base -ml-1 mr-2">check</span>
                    <span>Approve</span>
                  </button>
                </div>
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </main>
      <KeyboardShortcutsDialog open={showShortcuts} onOpenChange={setShowShortcuts} />
    </div>
  );
}
