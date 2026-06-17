import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Upload from './pages/Upload'
import Records from './pages/Records'
import Analytics from './pages/Analytics'
import Copilot from './pages/Copilot'
import EnforcementDashboard from './pages/EnforcementDashboard'
import TrafficIntelligenceCenter from './pages/TrafficIntelligenceCenter'
import Validation from './pages/Validation'
import Architecture from './pages/Architecture'
import Deployment from './pages/Deployment'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/records" element={<Records />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/enforcement" element={<EnforcementDashboard />} />
        <Route path="/intel-center" element={<TrafficIntelligenceCenter />} />
        <Route path="/copilot" element={<Copilot />} />
        <Route path="/validation" element={<Validation />} />
        <Route path="/architecture" element={<Architecture />} />
        <Route path="/deployment" element={<Deployment />} />
      </Routes>
    </Layout>
  )
}
