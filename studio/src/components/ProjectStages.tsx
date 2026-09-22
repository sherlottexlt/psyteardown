import type { ProductProjectView } from "../api/types";
import { currentStage, stageOrder } from "../domain/project";

const stageLabels = {
  intent: "意图",
  problem: "问题模型",
  contract: "结果契约",
  theses: "产品论点",
  prototype: "可运行成果",
} as const;

export function ProjectStages({ view }: { view: ProductProjectView }) {
  const current = currentStage(view);
  const currentIndex = stageOrder.indexOf(current);
  return (
    <ol className="stage-track" aria-label="产品进展阶段">
      {stageOrder.map((stage, index) => (
        <li
          className={index < currentIndex ? "is-done" : index === currentIndex ? "is-current" : ""}
          key={stage}
        >
          <span className="stage-track__dot">{index < currentIndex ? "✓" : index + 1}</span>
          <span>{stageLabels[stage]}</span>
        </li>
      ))}
    </ol>
  );
}
