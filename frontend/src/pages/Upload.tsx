import { useState, useCallback } from 'react';
import { useInvoice } from '@/context/InvoiceContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Upload as UploadIcon, File as FileIcon, Loader2, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

export default function Upload() {
    const { uploadInvoice } = useInvoice();
    const navigate = useNavigate();
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback(async (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files);
        if (files.length === 0) return;

        const pdfFiles = files.filter(file => file.type === 'application/pdf');

        if (pdfFiles.length !== files.length) {
            toast.error('Only PDF files are supported');
            return;
        }

        await processFiles(pdfFiles);
    }, []);

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files);
            await processFiles(files);
        }
    };

    const processFiles = async (files: File[]) => {
        setIsUploading(true);
        try {
            // New logic: individual files being uploaded
            for (const file of files) {
                await uploadInvoice(file);
            }
            // Success is handled by InvoiceContext and navigate
            navigate('/dashboard');
        } catch (error) {
            console.error(error);
            // Error toast also in InvoiceContext, but good to have a catch-all
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto space-y-8">
            <div className="text-center space-y-2">
                <h1 className="text-3xl font-bold">Upload Invoices</h1>
                <p className="text-muted-foreground">Drag and drop your PDF invoices here to start processing.</p>
            </div>

            <Card className={`border-2 border-dashed transition-colors ${isDragging ? 'border-primary bg-primary/5' : 'border-border'
                }`}>
                <CardContent className="flex flex-col items-center justify-center py-16 space-y-6">
                    <div className={`p-4 rounded-full ${isUploading ? 'bg-muted' : 'bg-primary/10'}`}>
                        {isUploading ? (
                            <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
                        ) : (
                            <UploadIcon className="h-10 w-10 text-primary" />
                        )}
                    </div>

                    <div className="text-center space-y-2">
                        <h3 className="text-lg font-semibold">
                            {isUploading ? 'Processing Invoices...' : 'Drag & Drop PDFs here'}
                        </h3>
                        <p className="text-sm text-muted-foreground max-w-xs mx-auto">
                            {isUploading
                                ? 'We are extracting data from your documents. This may take a moment.'
                                : 'Or click to browse files from your computer'
                            }
                        </p>
                    </div>

                    {!isUploading && (
                        <div className="relative">
                            <input
                                type="file"
                                accept=".pdf"
                                multiple
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                onChange={handleFileSelect}
                            />
                            <Button variant="secondary">
                                Select Files
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>


        </div>
    );
}
