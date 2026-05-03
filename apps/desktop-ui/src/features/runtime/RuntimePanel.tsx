import { Activity, Save } from "lucide-react";

import { CollapsibleSection } from "../../components/CollapsibleSection";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import type { RuntimeState } from "../../lib/types";

export function RuntimePanel({
  state,
  onSaveProfile
}: {
  state: RuntimeState;
  onSaveProfile: () => void;
}) {
  return (
    <CollapsibleSection title="Runtime" icon={<Activity size={16} />}>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <Badge tone={state.running ? "success" : "neutral"}>
          <Activity size={12} /> {state.running ? "running" : "idle"}
        </Badge>
        <Badge tone={state.recording ? "warning" : "neutral"}>
          {state.recording ? "recording" : "not recording"}
        </Badge>
        <Button className="col-span-2" variant="default" onClick={onSaveProfile}>
          <Save size={16} /> Save profile
        </Button>
      </div>
    </CollapsibleSection>
  );
}
