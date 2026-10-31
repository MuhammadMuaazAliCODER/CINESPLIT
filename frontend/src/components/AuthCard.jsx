export default function AuthCard({ eyebrow = 'CINESPLIT', title, description, children, footer }) {
  return (
    <section className="auth-card" aria-labelledby="auth-title">
      <span className="eyebrow">{eyebrow}</span>
      <h1 id="auth-title">{title}</h1>
      <p className="auth-description">{description}</p>
      {children}
      {footer && <div className="auth-footer">{footer}</div>}
    </section>
  )
}
