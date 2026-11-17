import React, { useState } from 'react'
import { exportCSV, exportPDF } from '../../api/admin'
import Navbar from '../../components/Navbar'
import toast from 'react-hot-toast'
import { Download, FileText } from 'lucide-react'

export default function AdminReports() {
  const [filters, setFilters] = useState({ start_date: '', end_date: '', department: '' })
  const [loading, setLoading] = useState('')

  const handleDownload = async (type) => {
    setLoading(type)
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([,v]) => v))
      const res = type === 'csv' ? await exportCSV(params) : await exportPDF(params)
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `complaints-report.${type}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`${type.toUpperCase()} downloaded!`)
    } catch (err) { toast.error(err.response?.data?.detail || 'Export failed') }
    finally { setLoading('') }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Reports & Exports</h1>

        <div className="card mb-6">
          <h2 className="font-semibold text-gray-900 mb-4">Filter Options</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input type="date" className="input-field" value={filters.start_date}
                onChange={e => setFilters({...filters, start_date: e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input type="date" className="input-field" value={filters.end_date}
                onChange={e => setFilters({...filters, end_date: e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
              <input className="input-field" placeholder="e.g. Engineering" value={filters.department}
                onChange={e => setFilters({...filters, department: e.target.value})} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="card text-center">
            <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center mx-auto mb-4">
              <Download className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">CSV Export</h3>
            <p className="text-sm text-gray-500 mb-4">Up to 10,000 complaints in spreadsheet format</p>
            <button onClick={() => handleDownload('csv')} disabled={loading === 'csv'} className="btn-primary w-full">
              {loading === 'csv' ? 'Generating...' : 'Download CSV'}
            </button>
          </div>
          <div className="card text-center">
            <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center mx-auto mb-4">
              <FileText className="w-6 h-6 text-red-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">PDF Report</h3>
            <p className="text-sm text-gray-500 mb-4">Up to 1,000 complaints formatted as a PDF</p>
            <button onClick={() => handleDownload('pdf')} disabled={loading === 'pdf'} className="btn-primary w-full">
              {loading === 'pdf' ? 'Generating...' : 'Download PDF'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
