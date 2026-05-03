import { Crosshair, Keyboard, MousePointerClick, Timer } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Button } from "../../components/ui/button";
import type { ActionStep } from "../../lib/types";

export function ActionLibrary({ onAdd }: { onAdd: (type: ActionStep["type"]) => void }) {
  return (
    <CollapsibleSection title="Action Library" icon={<MousePointerClick size={16} />}>
      <div className="grid gap-2">
        <Button variant="default" className="justify-start" onClick={() => onAdd("click")}>
          <MousePointerClick size={16} /> Click
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("wait")}>
          <Timer size={16} /> Wait
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("pixel_check")}>
          <Crosshair size={16} /> Pixel check
        </Button>
        <Button variant="default" className="justify-start" onClick={() => onAdd("key_tap")}>
          <Keyboard size={16} /> Key tap
        </Button>
      </div>
    </CollapsibleSection>
  );
}
