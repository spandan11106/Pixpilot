interface SectionHeadProps {
  overline: string;
  heading: string;
  hint: string;
}

export function SectionHead({ overline, heading, hint }: SectionHeadProps) {
  return (
    <div className="sect-head">
      <div className="ov">
        <span className="overline">{overline}</span>
        <h2>{heading}</h2>
      </div>
      <span className="sect-hint">{hint}</span>
    </div>
  );
}
