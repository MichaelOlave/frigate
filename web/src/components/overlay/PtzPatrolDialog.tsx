import axios from "axios";
import { useEffect, useMemo, useState } from "react";
import { MdDelete, MdRoute } from "react-icons/md";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { CameraPtzInfo, PtzPatrolStep } from "@/types/ptz";

type Props = {
  camera: string;
  ptz: CameraPtzInfo;
  refresh: () => Promise<CameraPtzInfo | undefined>;
};

export default function PtzPatrolDialog({ camera, ptz, refresh }: Props) {
  const [open, setOpen] = useState(false);
  const [presetName, setPresetName] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("");
  const [enabled, setEnabled] = useState(ptz.patrol.enabled);
  const [steps, setSteps] = useState<PtzPatrolStep[]>(ptz.patrol.steps);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setEnabled(ptz.patrol.enabled);
    setSteps(ptz.patrol.steps);
    setSelectedPreset(ptz.presets[0] ?? "");
  }, [open, ptz]);

  const usedPresets = useMemo(
    () => new Set(steps.map((step) => step.preset)),
    [steps],
  );

  const errorMessage = (error: unknown) => {
    if (axios.isAxiosError(error)) {
      return error.response?.data?.message ?? error.message;
    }
    return String(error);
  };

  const savePreset = async () => {
    const name = presetName.trim();
    if (!name) return;
    try {
      await axios.post(`${camera}/ptz/preset`, { name });
      setPresetName("");
      await refresh();
      toast.success(`Saved PTZ preset “${name}”.`);
    } catch (error) {
      toast.error(`Unable to save preset: ${errorMessage(error)}`);
    }
  };

  const deletePreset = async (preset: string) => {
    try {
      await axios.delete(`${camera}/ptz/preset/${encodeURIComponent(preset)}`);
      await refresh();
      toast.success(`Deleted PTZ preset “${preset}”.`);
    } catch (error) {
      toast.error(`Unable to delete preset: ${errorMessage(error)}`);
    }
  };

  const addStep = () => {
    if (!selectedPreset) return;
    setSteps((current) => [...current, { preset: selectedPreset, dwell: 10 }]);
  };

  const moveStep = (index: number, offset: number) => {
    const next = [...steps];
    const target = index + offset;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setSteps(next);
  };

  const savePatrol = async () => {
    setSaving(true);
    try {
      await axios.put(`${camera}/ptz/patrol`, { enabled, steps });
      await refresh();
      toast.success("Patrol path saved.");
      setOpen(false);
    } catch (error) {
      toast.error(`Unable to save patrol: ${errorMessage(error)}`);
    } finally {
      setSaving(false);
    }
  };

  const setRunning = async (running: boolean) => {
    try {
      await axios.post(`${camera}/ptz/patrol/${running ? "start" : "stop"}`);
      await refresh();
      toast.success(running ? "Patrol started." : "Patrol stopped.");
    } catch (error) {
      toast.error(`Unable to change patrol: ${errorMessage(error)}`);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button aria-label="Configure PTZ patrol">
          <MdRoute />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90dvh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>PTZ patrol</DialogTitle>
          <DialogDescription>
            Save the current view as a preset, then arrange presets into a
            repeating patrol path. Manual PTZ movement pauses the patrol.
          </DialogDescription>
        </DialogHeader>

        <section className="space-y-3">
          <Label htmlFor={`${camera}-preset-name`}>Save current position</Label>
          <div className="flex gap-2">
            <Input
              id={`${camera}-preset-name`}
              value={presetName}
              maxLength={64}
              placeholder="Preset name"
              onChange={(event) => setPresetName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void savePreset();
              }}
            />
            <Button
              onClick={() => void savePreset()}
              disabled={!presetName.trim()}
            >
              Save
            </Button>
          </div>
          {ptz.presets.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {ptz.presets.map((preset) => (
                <div
                  key={preset}
                  className="flex items-center gap-1 rounded-md border px-2 py-1 text-sm"
                >
                  <span>{preset}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-6"
                    aria-label={`Delete ${preset}`}
                    disabled={usedPresets.has(preset)}
                    onClick={() => void deletePreset(preset)}
                  >
                    <MdDelete />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor={`${camera}-patrol-enabled`}>
                Start automatically
              </Label>
              <p className="text-sm text-muted-foreground">
                Start this path whenever Frigate starts.
              </p>
            </div>
            <Switch
              id={`${camera}-patrol-enabled`}
              checked={enabled}
              onCheckedChange={setEnabled}
            />
          </div>

          <div className="flex gap-2">
            <Select value={selectedPreset} onValueChange={setSelectedPreset}>
              <SelectTrigger>
                <SelectValue placeholder="Select a preset" />
              </SelectTrigger>
              <SelectContent>
                {ptz.presets.map((preset) => (
                  <SelectItem key={preset} value={preset}>
                    {preset}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={addStep} disabled={!selectedPreset}>
              Add to path
            </Button>
          </div>

          <div className="space-y-2">
            {steps.map((step, index) => (
              <div
                key={`${step.preset}-${index}`}
                className="grid grid-cols-[1fr_6rem_auto] items-center gap-2 rounded-md border p-2"
              >
                <span className="truncate">{step.preset}</span>
                <div className="flex items-center gap-1">
                  <Input
                    aria-label={`${step.preset} dwell seconds`}
                    type="number"
                    min={1}
                    max={3600}
                    value={step.dwell}
                    onChange={(event) => {
                      const next = [...steps];
                      next[index] = {
                        ...step,
                        dwell: Math.max(1, Number(event.target.value) || 1),
                      };
                      setSteps(next);
                    }}
                  />
                  <span className="text-xs text-muted-foreground">s</span>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    aria-label={`Move ${step.preset} up`}
                    disabled={index === 0}
                    onClick={() => moveStep(index, -1)}
                  >
                    ↑
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    aria-label={`Move ${step.preset} down`}
                    disabled={index === steps.length - 1}
                    onClick={() => moveStep(index, 1)}
                  >
                    ↓
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove ${step.preset} from patrol`}
                    onClick={() =>
                      setSteps((current) =>
                        current.filter((_, itemIndex) => itemIndex !== index),
                      )
                    }
                  >
                    <MdDelete />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {ptz.patrol.last_error && (
          <p className="text-sm text-destructive">{ptz.patrol.last_error}</p>
        )}

        <DialogFooter className="gap-2 sm:justify-between">
          <div className="flex gap-2">
            {ptz.patrol.running ? (
              <Button
                variant="secondary"
                onClick={() => void setRunning(false)}
              >
                Stop patrol
              </Button>
            ) : (
              <Button
                variant="secondary"
                disabled={ptz.patrol.steps.length < 2}
                onClick={() => void setRunning(true)}
              >
                Start saved patrol
              </Button>
            )}
          </div>
          <Button
            onClick={() => void savePatrol()}
            disabled={saving || (enabled && steps.length < 2)}
          >
            {saving ? "Saving…" : "Save path"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
