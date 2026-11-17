import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createComplaint, listCategories } from '../../api/complaints'
import Navbar from '../../components/Navbar'
import toast from 'react-hot-toast'
import { Send, ArrowLeft } from 'lucide-react'

export default function SubmitComplaint() {
  const [form, setForm] = useState({ title: '', description: '', category_id: '' })
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    listCategories().then(r => setCategories(r.data)).catch(() => {})
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = {
        title: form.title,
        description: form.description,
        category_id: form.category_id ? parseInt(form.category_id) : null,
      }
      const res = await createComplaint(payload)
      toast.success(`Complaint ${res.data.reference_id} submitted!`)
      navigate('/citizen/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-2xl mx-auto px-4 py-8">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-blue-600 mb-6">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="card">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Submit a Complaint</h1>
            <p className="text-gray-500 mt-1">Describe your issue and we'll look into it</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Title <span className="text-red-500">*</span>
              </label>
              <input className="input-field" placeholder="Brief summary of your complaint"
                value={form.title} maxLength={100}
                onChange={(e) => setForm({ ...form, title: e.target.value })} required />
              <p className="text-xs text-gray-400 mt-1">{form.title.length}/100</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Category</label>
              <select className="input-field" value={form.category_id}
                onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                <option value="">Select a category (optional)</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Description <span className="text-red-500">*</span>
              </label>
              <textarea className="input-field min-h-[160px] resize-none"
                placeholder="Describe your complaint in detail..."
                value={form.description} maxLength={2000}
                onChange={(e) => setForm({ ...form, description: e.target.value })} required />
              <p className="text-xs text-gray-400 mt-1">{form.description.length}/2000</p>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              <Send className="w-4 h-4" />
              {loading ? 'Submitting...' : 'Submit Complaint'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
