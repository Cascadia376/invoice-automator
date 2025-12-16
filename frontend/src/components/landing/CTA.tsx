import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export const CTA = () => {
  return (
    <section className="py-20 md:py-28">
      <div className="container">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-primary p-12 md:p-16 lg:p-20 text-center">
          {/* Background Effects */}
          <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,.05)_50%,transparent_75%,transparent_100%)] bg-[length:250px_250px] animate-[shimmer_3s_linear_infinite]" />
          
          <div className="relative z-10">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-6">
              Ready to save 8+ hours per week?
            </h2>
            <p className="text-lg md:text-xl text-white/90 max-w-2xl mx-auto mb-10">
              Join 300+ early adopters who chose to fund our MVP instead of waiting for VC-backed features they don't need.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="xl" variant="glass" className="group bg-white hover:bg-white/90 text-primary">
                Get Lifetime Access
                <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Button>
              <Button size="xl" variant="outline" className="border-white/20 text-white hover:bg-white/10">
                Schedule a Demo
              </Button>
            </div>
            <p className="mt-8 text-sm text-white/80">
              🎯 Limited to first 500 customers • 💳 One-time payment • ⚡ Instant access
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
