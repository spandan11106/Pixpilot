"use client";

import { useCallback, forwardRef } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

export type VisionProvider = "openai" | "anthropic" | "google";

const PROVIDER_META: Record<VisionProvider, { name: string; initials: string; bg: string; color: string }> = {
  openai: { name: "OpenAI", initials: "OA", bg: "rgba(var(--green-rgb),0.18)", color: "var(--green)" },
  anthropic: { name: "Anthropic", initials: "AN", bg: "rgba(var(--accent2-rgb),0.2)", color: "var(--accent-2)" },
  google: { name: "Google", initials: "GG", bg: "rgba(var(--primary-rgb),0.18)", color: "var(--primary)" },
};

const TIER_LABELS = ["Primary", "2nd fallback", "3rd fallback"];

const DragHandle = forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  function DragHandle(props, ref) {
    return (
      <span ref={ref} className="p-handle" aria-label="Drag to reorder" {...props}>
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <circle cx="9" cy="6" r="1.4" />
          <circle cx="15" cy="6" r="1.4" />
          <circle cx="9" cy="12" r="1.4" />
          <circle cx="15" cy="12" r="1.4" />
          <circle cx="9" cy="18" r="1.4" />
          <circle cx="15" cy="18" r="1.4" />
        </svg>
      </span>
    );
  }
);

interface SortableItemProps {
  id: VisionProvider;
  index: number;
}

function SortableItem({ id, index }: SortableItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const meta = PROVIDER_META[id];
  const isPrimary = index === 0;

  return (
    <div
      ref={setNodeRef}
      className={`prio-item${isPrimary ? " prio-primary" : ""}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
        zIndex: isDragging ? 10 : undefined,
      }}
      {...attributes}
    >
      <DragHandle ref={setActivatorNodeRef} {...listeners} />

      <span className={`p-rank${isPrimary ? " p-rank-primary" : ""}`}>
        {index + 1}
      </span>

      <span className="p-name">
        <span
          className="prov-mark"
          style={{ width: 28, height: 28, fontSize: 11, background: meta.bg, color: meta.color }}
        >
          {meta.initials}
        </span>
        {meta.name}
      </span>

      <span className={`p-tier${isPrimary ? " p-tier-primary" : ""}`}>
        {TIER_LABELS[index] ?? `${index + 1}th fallback`}
      </span>
    </div>
  );
}

interface VisionPriorityProps {
  order: VisionProvider[];
  onChange: (order: VisionProvider[]) => void;
}

export function VisionPriority({ order, onChange }: VisionPriorityProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIndex = order.indexOf(active.id as VisionProvider);
      const newIndex = order.indexOf(over.id as VisionProvider);
      onChange(arrayMove(order, oldIndex, newIndex));
    },
    [order, onChange]
  );

  return (
    <div className="card prio">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          <div className="prio-list">
            {order.map((id, index) => (
              <SortableItem key={id} id={id} index={index} />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="prio-foot">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        Drag the handles to change priority. If a provider fails or is rate-limited, the next one takes over automatically.
      </div>
    </div>
  );
}
