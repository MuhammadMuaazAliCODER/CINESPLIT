import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faEye, faEyeSlash } from '@fortawesome/free-solid-svg-icons'

export default function FormField({ label, id, type = 'text', error, ...props }) {
  const [visible, setVisible] = useState(false)
  const isPassword = type === 'password'

  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      {isPassword ? (
        <div className="password-field">
          <input id={id} name={id} type={visible ? 'text' : 'password'} className="password-input" aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} {...props} />
          <button
            className="password-toggle"
            type="button"
            aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
            aria-controls={id}
            aria-pressed={visible}
            onClick={() => setVisible((value) => !value)}
          >
            <FontAwesomeIcon icon={visible ? faEyeSlash : faEye} aria-hidden="true" />
          </button>
        </div>
      ) : (
        <input id={id} name={id} type={type} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} {...props} />
      )}
      {error && <span id={`${id}-error`} className="field-error">{error}</span>}
    </div>
  )
}
