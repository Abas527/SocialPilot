import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { errorMessage } from '../lib/format'
import { useAppTheme } from '../theme/ThemeContext'
import { useFlash } from './Flash'
import { ImportProjectModal } from './ImportProjectModal'
import type { ImportMode } from './ImportProjectModal'

/** Owns the import form state; opens the existing modal and routes to the new project. */
export function ImportProjectController({ onClose }: { onClose: () => void }) {
  const { theme } = useAppTheme()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const flash = useFlash()
  const [mode, setMode] = useState<ImportMode>('github')
  const [repoUrl, setRepoUrl] = useState('')
  const [readme, setReadme] = useState('')

  const importProject = useMutation({
    mutationFn: () => api<{ project_id: string }>('/projects/import', {
      method: 'POST',
      body: JSON.stringify(mode === 'github' ? { repo_url: repoUrl } : { pasted_readme: readme }),
    }),
    onSuccess: async ({ project_id }) => {
      await qc.invalidateQueries({ queryKey: ['projects'] })
      onClose()
      navigate(`/app/projects/${project_id}`)
      flash.showNotice('Project imported. Analyze it to build your project profile.')
    },
    onError: (cause) => flash.showError(errorMessage(cause)),
  })

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    importProject.mutate()
  }

  return (
    <ImportProjectModal
      theme={theme}
      mode={mode}
      repoUrl={repoUrl}
      readme={readme}
      loading={importProject.isPending}
      onModeChange={setMode}
      onRepoUrlChange={setRepoUrl}
      onReadmeChange={setReadme}
      onClose={onClose}
      onSubmit={submit}
    />
  )
}
