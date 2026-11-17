import { useState, useEffect } from 'react'
import { listComplaints } from '../api/complaints'
import toast from 'react-hot-toast'

export function useComplaints() {
  const [complaints, setComplaints] = useState([])
  const [loading, setLoading] = useState(true)

  const fetch = async () => {
    try {
      setLoading(true)
      const res = await listComplaints()
      setComplaints(res.data)
    } catch {
      toast.error('Failed to load complaints')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetch() }, [])
  return { complaints, loading, refetch: fetch }
}
