import { MapPin, ShieldCheck, Star, Zap, Clock, Phone, Mail } from 'lucide-react'

const SERVICES = [
  { name: 'Cleaning', desc: 'Need Cleaner for 2-Bedroom in Yaba - Today', price: '₦8,000 per day', loc: 'Yaba 1.2km', score: '93%' },
  { name: 'Plumbing', desc: 'Emergency Plumber Surulere - Burst Pipe', price: '₦15,000 per project', loc: 'Surulere 3.4km', score: '87%' },
  { name: 'Electrical', desc: 'Electrical Wiring - New 3-Bedroom Flat', price: '₦25,000 per project', loc: 'Ikeja 2.1km', score: '79%' },
  { name: 'Hairdressing', desc: 'Professional home service braids & styling', price: 'From ₦5,000', loc: 'Lagos', score: '92%' },
  { name: 'Tailoring', desc: 'Urgent Tailor - Aso Oke Modification', price: '₦8,000', loc: 'Maryland', score: '88%' },
]

export default function App() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-[#222] bg-black/90 backdrop-blur">
        <div className="mx-auto max-w-6xl flex h-[64px] items-center justify-between px-6">
          <h1 className="text-[22px] font-black tracking-[0.22em]">GIGGS</h1>
          <nav className="hidden md:flex gap-8 text-[13px] text-[#999]">
            <a href="#services">Services</a><a href="#how">How it Works</a><a href="#business">Business Info</a>
          </nav>
          <button className="h-[40px] rounded-full bg-white px-6 text-[13px] font-bold text-black">Book Artisan</button>
        </div>
      </header>

      {/* Hero - Matches your GIGGS SERVICES HUB banner */}
      <section className="border-b border-[#222] py-24 text-center">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-[720px] rounded-[24px] border border-[#222] bg-[#0A0A0A] p-12">
            <h1 className="text-[56px] font-black leading-none tracking-[0.22em]">GIGGS</h1>
            <p className="mt-3 text-[10px] tracking-[0.55em] text-[#666]">SERVICES HUB</p>
            <h2 className="mt-10 text-[32px] font-bold leading-tight">Trusted Cleaners, Plumbers & Artisans in Lagos</h2>
            <p className="mt-4 text-[14px] leading-[22px] text-[#999]">Book verified workers in Yaba, Surulere, Ikeja, Maryland. Cleaning, Plumbing, Electrical, Hairdressing, Tailoring. Distance 1.2km • Match 93% • Rating 4.7/5 • Trust 92</p>
            <div className="mt-8 flex justify-center gap-3">
              <button className="h-[48px] rounded-full bg-white px-8 font-bold text-black">Get Started</button>
              <button className="h-[48px] rounded-full border border-[#333] px-8">View Services</button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 border-b border-[#222] md:grid-cols-4">
        {[
          { k: '500+', v: 'Jobs Completed' },
          { k: '4.8/5', v: 'Average Rating' },
          { k: '1.2km', v: 'Avg Distance' },
          { k: '93%', v: 'Match Score' },
        ].map(s => (
          <div key={s.v} className="border-r border-[#222] p-8 text-center last:border-0">
            <p className="text-[28px] font-black">{s.k}</p><p className="text-[11px] text-[#666]">{s.v}</p>
          </div>
        ))}
      </section>

      {/* Services */}
      <section id="services" className="mx-auto max-w-6xl px-6 py-20">
        <h3 className="text-[24px] font-bold">Our Services</h3>
        <p className="mt-2 text-[13px] text-[#777]">All categories from your app: Cleaning, Plumbing, Electrical, Hairdressing, Tailoring — with TODAY / THIS WEEK / FLEXIBLE urgency</p>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {SERVICES.map(s => (
            <div key={s.name} className="rounded-[20px] border border-[#222] bg-[#0F0F0F] p-6">
              <div className="flex justify-between"><span className="text-[11px] tracking-wide text-[#666]">{s.name.toUpperCase()}</span><span className="rounded-full bg-white px-2 py-1 text-[10px] font-bold text-black">{s.score}</span></div>
              <h4 className="mt-4 text-[15px] font-semibold leading-tight">{s.desc}</h4>
              <p className="mt-3 flex items-center gap-2 text-[11px] text-[#666]"><MapPin size={12}/> {s.loc} • <Star size={12}/> 4.7 • <ShieldCheck size={12}/> 92 trust</p>
              <p className="mt-4 text-[14px] font-bold">{s.price}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How */}
      <section id="how" className="border-y border-[#222] bg-[#0A0A0A] py-20">
        <div className="mx-auto max-w-6xl px-6 grid md:grid-cols-3 gap-8">
          {[
            { tag: 'TODAY', title: 'Post Job', desc: 'Emergency Plumber Surulere - Burst Pipe. 12 views, 3 applicants in 15m' },
            { tag: 'THIS WEEK', title: 'Match & Pay', desc: '10% commission min ₦500 max ₦5,000. Escrow via Paystack. Booking protected.' },
            { tag: 'FLEXIBLE', title: 'Complete & Rate', desc: 'Rate worker ★★★★★. Trust 0-100 system. Elite, Trusted, Good, Average, Risky, Dangerous.' },
          ].map(i => (
            <div key={i.tag} className="rounded-[16px] border border-[#222] bg-black p-6">
              <span className="rounded-full border border-[#333] px-3 py-1 text-[10px] font-bold tracking-widest">{i.tag}</span>
              <h4 className="mt-4 font-bold">{i.title}</h4><p className="mt-2 text-[12px] text-[#777] leading-relaxed">{i.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Business Info - CRITICAL FOR MONNIFY */}
      <section id="business" className="mx-auto max-w-6xl px-6 py-20">
        <div className="rounded-[24px] border border-[#222] bg-[#0F0F0F] p-8">
          <h3 className="text-[18px] font-bold">Business Verification Information</h3>
          <p className="mt-2 text-[11px] text-[#666]">Required for Monnify / Payment Processor KYC</p>
          <div className="mt-8 grid gap-6 md:grid-cols-2 text-[13px]">
            <div><p className="text-[#666] text-[11px] uppercase">Business Name</p><p className="mt-1 font-semibold">Giggs Services Hub</p></div>
            <div><p className="text-[#666] text-[11px] uppercase">TIN</p><p className="mt-1 font-mono">2511008541959</p></div>
            <div><p className="text-[#666] text-[11px] uppercase">Staff Size</p><p className="mt-1">1-10</p></div>
            <div><p className="text-[#666] text-[11px] uppercase">Chargeback Email</p><p className="mt-1 flex gap-2"><Mail size={14}/> oluwafemiseyiashmi@gmail.com</p></div>
            <div className="md:col-span-2"><p className="text-[#666] text-[11px] uppercase">Business Address</p><p className="mt-1 flex gap-2"><MapPin size={14}/> No 12 Oduduwa Street, Ijapo Estate, Near Police Station, Akure, Ondo State. Service Areas: Yaba, Surulere, Ikeja, Maryland, Lagos</p></div>
            <div><p className="text-[#666] text-[11px] uppercase">Business Website</p><p className="mt-1">This website - Deployed on Render</p></div>
            <div><p className="text-[#666] text-[11px] uppercase">Support</p><p className="mt-1 flex gap-2"><Phone size={14}/> Lagos, Nigeria</p></div>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#222] py-10 text-center text-[11px] text-[#555]">
        <p className="tracking-[0.22em] font-black text-white">GIGGS</p>
        <p className="mt-2">© 2026 Giggs Services Hub • TIN 2511008541959 • No 12 Oduduwa Street, Ijapo, Akure</p>
      </footer>
    </div>
  )
}
