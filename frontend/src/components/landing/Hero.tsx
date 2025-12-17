import { Button } from "@/components/ui/button";
import { ArrowRight, Play } from "lucide-react";
import heroDashboard from "@/assets/hero-dashboard.jpg";

export const Hero = () => {
  return (
    <section className="relative overflow-hidden bg-gradient-subtle">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:14px_24px]" />
      <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />

      <div className="container relative">
        <div className="flex flex-col items-center text-center py-20 md:py-28 lg:py-32">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-background/50 backdrop-blur-sm mb-8 animate-fade-in">
            <span className="flex h-2 w-2 rounded-full bg-success animate-pulse" />
            <span className="text-sm font-medium">Limited Launch Offer: Lifetime Deal Available</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight max-w-5xl mb-6 animate-fade-up">
            Stop wasting time on{" "}
            <span className="gradient-text">invoice entry</span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 animate-fade-up" style={{ animationDelay: "0.1s" }}>
            AI-powered invoice processing that extracts, validates, and pushes data to your accounting software—automatically.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 mb-16 animate-fade-up" style={{ animationDelay: "0.2s" }}>
            <Button size="xl" variant="hero" className="group">
              Get Lifetime Access
              <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
            </Button>
            <Button size="xl" variant="glass">
              <Play className="mr-2 h-5 w-5" />
              Watch Demo
            </Button>
          </div>

          {/* Social Proof */}
          <div className="flex flex-col sm:flex-row items-center gap-6 text-sm text-muted-foreground mb-16 animate-fade-up" style={{ animationDelay: "0.3s" }}>
            <div className="flex -space-x-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-10 w-10 rounded-full border-2 border-background bg-muted flex items-center justify-center">
                  <span className="text-xs font-medium">{i}</span>
                </div>
              ))}
            </div>
            <p>
              <span className="font-semibold text-foreground">300+ early adopters</span> already saving time
            </p>
          </div>

          {/* Hero Image */}
          <div className="relative w-full max-w-6xl animate-fade-up" style={{ animationDelay: "0.4s" }}>
            <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent z-10" />
            <div className="relative rounded-2xl overflow-hidden border border-border shadow-2xl hover-lift">
              <img
                src={heroDashboard}
                alt="Cascadia Invoice Agent Dashboard"
                className="w-full h-auto"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
