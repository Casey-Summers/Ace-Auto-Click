import { Crosshair, Grab, Repeat, Keyboard, MousePointer, MousePointerClick, Timer } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Button } from "../../components/ui/button";
import type { ActionStep } from "../../lib/types";

export function ActionLibrary({ onAdd }: { onAdd: (type: ActionStep["type"]) => void }) {
  return (
    <CollapsibleSection title="Action Library">
      <div className="grid gap-2">
        <Button variant="default" className="justify-start" onClick={() => onAdd("click")}>
          <MousePointerClick size={16} /> Click
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("move")}>
          <MousePointer size={16} /> Move
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("drag")}>
          <Grab size={16} /> Drag
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("wait")}>
          <Timer size={16} /> Wait
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("pixel_check")}>
          <Crosshair size={16} /> Pixel Match
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("key_tap")}>
          <Keyboard size={16} /> Keybind Tap
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("key_hold")}>
          <Keyboard size={16} /> Keybind Hold
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("loop_start")}>
          <Repeat size={16} /> Loop
        </Button>
      </div>
    </CollapsibleSection>
  );
}
