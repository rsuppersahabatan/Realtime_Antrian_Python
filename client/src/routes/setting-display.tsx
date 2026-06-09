import { useEffect, useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import DisplaySetting from '../pages/DisplaySetting'

export const Route = createFileRoute('/setting-display')({ component: SettingDisplayRoute })

function SettingDisplayRoute() {
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

  return <DisplaySetting />
}
