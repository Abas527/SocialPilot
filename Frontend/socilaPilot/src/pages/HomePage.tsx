import { LandingPage } from '../landing/LandingPage'

type HomePageProps = {
  onOpenWorkspace: () => void
}

export function HomePage({ onOpenWorkspace }: HomePageProps) {
  return <LandingPage onOpenWorkspace={onOpenWorkspace} />
}
