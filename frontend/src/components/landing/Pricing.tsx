import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const tiers = [
  {
    name: "Solo",
    price: "$99",
    description: "Perfect for freelancers and micro businesses",
    features: [
      "200 invoices/month",
      "1 company",
      "Email upload",
      "Basic integrations",
      "Community support",
    ],
    cta: "Get Solo",
    popular: false,
  },
  {
    name: "Pro",
    price: "$249",
    description: "For bookkeepers and small firms",
    features: [
      "1,000 invoices/month",
      "3 companies",
      "Email + manual upload",
      "All integrations",
      "Priority support",
      "Advanced analytics",
    ],
    cta: "Get Pro",
    popular: true,
  },
  {
    name: "Agency",
    price: "$499",
    description: "For agencies and accounting teams",
    features: [
      "5,000 invoices/month",
      "10 companies",
      "All upload methods",
      "Custom integrations",
      "White-label option",
      "Dedicated account manager",
      "API access",
    ],
    cta: "Get Agency",
    popular: false,
  },
];

export const Pricing = () => {
  return (
    <section id="pricing" className="py-20 md:py-28 bg-muted/30">
      <div className="container">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-success-light text-success-foreground mb-6">
            <Sparkles className="h-4 w-4" />
            <span className="text-sm font-medium">Limited Time: Lifetime Deal</span>
          </div>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            Pay once, <span className="gradient-text">own it forever</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Join our first 500 customers. No monthly fees. No hidden costs.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {tiers.map((tier, index) => (
            <Card
              key={index}
              className={`relative border-border/50 hover-lift ${
                tier.popular ? "border-primary shadow-xl scale-105" : ""
              }`}
            >
              {tier.popular && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-primary border-0">
                  Most Popular
                </Badge>
              )}
              <CardHeader className="text-center pb-8">
                <CardTitle className="text-2xl mb-2">{tier.name}</CardTitle>
                <div className="mb-2">
                  <span className="text-4xl font-bold">{tier.price}</span>
                  <span className="text-muted-foreground ml-2">one-time</span>
                </div>
                <CardDescription>{tier.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {tier.features.map((feature, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <Check className="h-5 w-5 text-success shrink-0 mt-0.5" />
                    <span className="text-sm">{feature}</span>
                  </div>
                ))}
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full"
                  variant={tier.popular ? "hero" : "default"}
                  size="lg"
                >
                  {tier.cta}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>

        <div className="mt-12 text-center">
          <p className="text-sm text-muted-foreground mb-2">
            All plans include lifetime access to current features
          </p>
          <p className="text-xs text-muted-foreground">
            Limited to first 500 customers • Transition to subscription available post-launch
          </p>
        </div>
      </div>
    </section>
  );
};
