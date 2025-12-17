import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "What does 'lifetime' really mean?",
    answer:
      "Lifetime means you'll have access to the product and the feature tier you purchased for as long as we operate. You won't be charged again for the core features included in your tier.",
  },
  {
    question: "What happens after the LTD period ends?",
    answer:
      "After we close the lifetime deal, we'll transition to subscription pricing ($29-$99/month). LTD holders keep their access and can upgrade to new modules at discounted rates.",
  },
  {
    question: "Can I upgrade my tier later?",
    answer:
      "Yes! You can upgrade to a higher tier by paying the difference during the LTD period. After that, upgrades will be available through maintenance subscriptions.",
  },
  {
    question: "Which accounting software do you integrate with?",
    answer:
      "The current build focuses on export-ready data. Use CSV exports or your own API bridge to drop data into your accounting stack.",
  },
  {
    question: "What file formats do you support?",
    answer:
      "We extract data from PDF, PNG, JPG, and HEIC files. Invoices can be uploaded via email forwarding, drag-and-drop, or mobile app.",
  },
  {
    question: "Is my financial data secure?",
    answer:
      "Absolutely. We use bank-grade encryption (AES-256), are SOC 2 compliant, and never store your accounting credentials. All data is encrypted in transit and at rest.",
  },
];

export const FAQ = () => {
  return (
    <section id="faq" className="py-20 md:py-28">
      <div className="container max-w-3xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            Frequently asked questions
          </h2>
          <p className="text-lg text-muted-foreground">
            Everything you need to know about the lifetime deal
          </p>
        </div>

        <Accordion type="single" collapsible className="space-y-4">
          {faqs.map((faq, index) => (
            <AccordionItem
              key={index}
              value={`item-${index}`}
              className="border border-border/50 rounded-lg px-6 bg-card"
            >
              <AccordionTrigger className="text-left hover:no-underline">
                <span className="font-semibold">{faq.question}</span>
              </AccordionTrigger>
              <AccordionContent className="text-muted-foreground">
                {faq.answer}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
};
