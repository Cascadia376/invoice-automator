import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Command, Save, CheckCircle, ChevronLeft, ChevronRight, Columns } from "lucide-react";

interface KeyboardShortcutsDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function KeyboardShortcutsDialog({ open, onOpenChange }: KeyboardShortcutsDialogProps) {
    const shortcuts = [
        { icon: <Save className="h-4 w-4" />, label: "Save Changes", keys: ["⌘", "S"] },
        { icon: <CheckCircle className="h-4 w-4" />, label: "Approve Invoice", keys: ["⌘", "Enter"] },
        { icon: <ChevronRight className="h-4 w-4" />, label: "Next Invoice", keys: ["J"] },
        { icon: <ChevronLeft className="h-4 w-4" />, label: "Previous Invoice", keys: ["K"] },
        { icon: <Columns className="h-4 w-4" />, label: "Toggle Columns", keys: ["⌘", "\\"] },
        { icon: <Command className="h-4 w-4" />, label: "Show Shortcuts", keys: ["?"] },
    ];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Keyboard Shortcuts</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    {shortcuts.map((shortcut, index) => (
                        <div key={index} className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                {shortcut.icon}
                                <span>{shortcut.label}</span>
                            </div>
                            <div className="flex gap-1">
                                {shortcut.keys.map((key, kIndex) => (
                                    <kbd
                                        key={kIndex}
                                        className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100"
                                    >
                                        {key}
                                    </kbd>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </DialogContent>
        </Dialog>
    );
}
