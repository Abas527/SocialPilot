type PageHeadingProps = {
  eyebrow: string
  title: string
  subtitle: string
}

export function PageHeading({ eyebrow, title, subtitle }: PageHeadingProps) {
  return (
    <div className="page-heading">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
  )
}
