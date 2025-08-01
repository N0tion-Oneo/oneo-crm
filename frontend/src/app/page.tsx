import { redirect } from 'next/navigation'

export default function HomePage() {
  // Redirect to login page - will be updated to handle tenant detection
  redirect('/login')
}