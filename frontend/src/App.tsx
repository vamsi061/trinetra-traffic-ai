import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Upload from './pages/Upload'
import Records from './pages/Records'
import Analytics from './pages/Analytics'
import Copilot from './pages/Copilot'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/records" element={<Records />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/copilot" element={<Copilot />} />
      </Routes>
    </Layout>
  )
}
