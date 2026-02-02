
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Download } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

const Reports = () => {
    const { toast } = useToast();
    const [startDate, setStartDate] = useState(() => {
        const date = new Date();
        date.setDate(1); // First day of current month
        return date.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
    const [loading, setLoading] = useState(false);

    const handleDownload = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('supabase_token'); // Assuming auth
            const headers: HeadersInit = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/reports/receiving-summary?start_date=${startDate}&end_date=${endDate}`,
                {
                    method: 'GET',
                    headers
                }
            );

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to download report');
            }

            // Trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `receiving_summary_${startDate}_${endDate}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast({
                title: "Report Downloaded",
                description: "Your CSV report has been generated successfully.",
            });

        } catch (error: any) {
            console.error(error);
            toast({
                title: "Download Failed",
                description: error.message,
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mx-auto p-6 max-w-4xl">
            <h1 className="text-3xl font-bold mb-8">Reports</h1>

            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Receiving Summary</CardTitle>
                        <CardDescription>
                            Generate a CSV breakdown of all received invoices by product category (Beer, Wine, Spirits, etc.).
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="start-date">Start Date</Label>
                                <Input
                                    id="start-date"
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="end-date">End Date</Label>
                                <Input
                                    id="end-date"
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                />
                            </div>
                        </div>

                        <Button
                            className="w-full"
                            onClick={handleDownload}
                            disabled={loading}
                        >
                            {loading ? (
                                "Generating..."
                            ) : (
                                <>
                                    <Download className="mr-2 h-4 w-4" /> Download CSV
                                </>
                            )}
                        </Button>
                    </CardContent>
                </Card>

                {/* Placeholder for future reports */}
                <Card className="opacity-50">
                    <CardHeader>
                        <CardTitle>Vendor Variance Report</CardTitle>
                        <CardDescription>
                            Coming Soon: Analyze price discrepancies and missing items by vendor.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button disabled variant="outline" className="w-full">Coming Soon</Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default Reports;
