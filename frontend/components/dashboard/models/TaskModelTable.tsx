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

export type TaskProvider = string;

export interface TaskProviderDef {
  id: TaskProvider;
  name: string;
  initials: string;
  bg: string;
  color: string;
  modelField: string;
  placeholder: string;
}

interface TaskModelTableProps {
  providers: TaskProviderDef[];
  order: TaskProvider[];
  models: Record<string, string>;
  onOrderChange: (order: TaskProvider[]) => void;
  onModelChange: (field: string, value: string) => void;
}

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

interface SortableRowProps {
  provider: TaskProviderDef;
  index: number;
  modelValue: string;
  onModelChange: (field: string, value: string) => void;
}

function SortableRow({ provider, index, modelValue, onModelChange }: SortableRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: provider.id });

  const isPrimary = index === 0;

  return (
    <div
      ref={setNodeRef}
      className={`task-row${isPrimary ? " task-row-primary" : ""}`}
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

      <span className="task-row-prov">
        <span
          className="prov-mark"
          style={{ width: 28, height: 28, fontSize: 11, background: provider.bg, color: provider.color }}
        >
          {provider.initials}
        </span>
        <span className="task-row-meta">
          <span className="field-label">{provider.name}</span>
          <span className={`p-tier${isPrimary ? " p-tier-primary" : ""}`}>
            {TIER_LABELS[index] ?? `${index + 1}th fallback`}
          </span>
        </span>
      </span>

      <input
        className="finput mono task-row-input"
        type="text"
        value={modelValue}
        onChange={(e) => onModelChange(provider.modelField, e.target.value)}
        placeholder={provider.placeholder}
        aria-label={`${provider.name} model`}
      />
    </div>
  );
}

export function TaskModelTable({
  providers,
  order,
  models,
  onOrderChange,
  onModelChange,
}: TaskModelTableProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIndex = order.indexOf(active.id as TaskProvider);
      const newIndex = order.indexOf(over.id as TaskProvider);
      onOrderChange(arrayMove(order, oldIndex, newIndex));
    },
    [order, onOrderChange]
  );

  const orderedProviders = order
    .map((id) => providers.find((p) => p.id === id))
    .filter((p): p is TaskProviderDef => Boolean(p));

  return (
    <div className="card task-table">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          <div className="task-list">
            {orderedProviders.map((provider, index) => (
              <SortableRow
                key={provider.id}
                provider={provider}
                index={index}
                modelValue={models[provider.modelField] ?? ""}
                onModelChange={onModelChange}
              />
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
        Drag handles to set priority. Pixpilot tries providers top-to-bottom on failure or rate-limit.
      </div>
    </div>
  );
}
