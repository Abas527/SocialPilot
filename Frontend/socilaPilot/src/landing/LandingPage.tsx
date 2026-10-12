import { Footer } from './components/Footer'
import { Navbar } from './components/Navbar'
import { BlockchainTipsSection } from './sections/BlockchainTipsSection'
import { CommunitySection } from './sections/CommunitySection'
import { FinalCTA } from './sections/FinalCTA'
import { HeroSection } from './sections/HeroSection'
import { HowItWorksSection } from './sections/HowItWorksSection'
import { MVPSection } from './sections/MVPSection'
import { ProblemSection } from './sections/ProblemSection'
import { RagSection } from './sections/RagSection'
import { SolutionSection } from './sections/SolutionSection'
import { VisionSection } from './sections/VisionSection'

type LandingPageProps = {
  onOpenWorkspace: () => void
}

export function LandingPage({ onOpenWorkspace }: LandingPageProps) {
  return (
    <div className="landing-page min-h-screen bg-[#070b16] text-slate-200">
      <Navbar onOpenWorkspace={onOpenWorkspace} />
      <main>
        <HeroSection onOpenWorkspace={onOpenWorkspace} />
        <ProblemSection />
        <SolutionSection />
        <HowItWorksSection />
        <RagSection />
        <CommunitySection />
        <BlockchainTipsSection />
        <MVPSection />
        <VisionSection />
        <FinalCTA onOpenWorkspace={onOpenWorkspace} />
      </main>
      <Footer onOpenWorkspace={onOpenWorkspace} />
    </div>
  )
}
