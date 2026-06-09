import { useEffect, useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import Display from '../pages/Display'

export const Route = createFileRoute('/display-client')({ component: DisplayClientRoute })

function DisplayClientRoute() {
  const navigate = useNavigate()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      navigate({ to: '/login', replace: true })
      return
    }
    setChecked(true)
  }, [navigate])

  if (!checked) return null

  return <Display />
}
