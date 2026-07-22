import { createClient } from '@supabase/supabase-js'
import { mockPersonas } from './data/mockPersonas'
import { mockProducts } from './data/mockProducts'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// If env vars aren't set (e.g. first run, before Supabase is wired up),
// isConfigured stays false and every fetch below silently uses the local
// mock data instead — no crash, no blank screen.
export const isConfigured = Boolean(url && anonKey && !url.includes('your-project'))

export const supabase = isConfigured ? createClient(url, anonKey) : null

export async function fetchPersonas() {
  if (!isConfigured) return mockPersonas
  const { data, error } = await supabase.from('personas').select('*')
  if (error) {
    console.warn('Supabase fetchPersonas failed, falling back to mock data:', error.message)
    return mockPersonas
  }
  return data
}

export async function fetchProducts() {
  if (!isConfigured) return mockProducts
  const { data, error } = await supabase.from('products').select('*')
  if (error) {
    console.warn('Supabase fetchProducts failed, falling back to mock data:', error.message)
    return mockProducts
  }
  return data
}

export async function logEvent({ personaId, productId, action }) {
  if (!isConfigured) {
    console.log('[event_log - mock mode, not persisted]', { personaId, productId, action })
    return
  }
  const { error } = await supabase
    .from('event_log')
    .insert({ persona_id: personaId, product_id: productId, action })
  if (error) {
    console.warn('Supabase logEvent failed:', error.message)
  }
}
