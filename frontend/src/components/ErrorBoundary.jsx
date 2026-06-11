import { Component } from 'react'

// Error boundaries must be class components — React has no hook equivalent.
// Catches render-time crashes in any page so the whole app doesn't white-screen.
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="mx-auto max-w-xl rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="font-medium text-red-800">Something went wrong.</p>
        <p className="mt-1 text-sm text-red-700">{this.state.error.message}</p>
        <button
          onClick={() => { this.setState({ error: null }); window.location.assign('/') }}
          className="mt-4 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
        >
          Back to projects
        </button>
      </div>
    )
  }
}
