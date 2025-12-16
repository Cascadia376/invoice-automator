import { CheckCircle2, Zap, Lock, BarChart3, RefreshCw, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    icon: Zap,
    title: "Lightning Fast Extraction",
    description: "Advanced AI extracts invoice data in seconds. No manual typing, no errors.",
  },
  {
    icon: CheckCircle2,
    title: "Smart Validation",
    description: "Automatic field validation and duplicate detection before data hits your books.",
  },
  {
    icon: RefreshCw,
    title: "Direct Integration",
    description: "Push to QuickBooks, Xero, or your ERP with one click. No exports, no imports.",
  },
  {
    icon: Lock,
    title: "Bank-Grade Security",
    description: "SOC 2 compliant infrastructure. Your financial data stays encrypted and safe.",
  },
  {
    icon: BarChart3,
    title: "Real-Time Analytics",
    description: "Track processing status, vendor patterns, and time savings at a glance.",
  },
  {
    icon: Users,
    title: "Multi-Company Support",
    description: "Manage invoices for multiple entities from a single dashboard.",
  },
];

export const Features = () => {
  return (
    <section id="features" className="py-20 md:py-28">
      <div className="container">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            Everything you need to <span className="gradient-text">automate invoices</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            From email to accounting software in minutes—not hours.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <Card
              key={index}
              className="border-border/50 hover:border-primary/50 transition-all duration-300 hover-lift"
            >
              <CardHeader>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-light mb-4">
                  <feature.icon className="h-6 w-6 text-primary" />
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base">{feature.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};
