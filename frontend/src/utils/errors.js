export function getApiErrorMessage(error, fallback = 'Ha ocurrido un error.') {
  const code = error?.response?.data?.error?.code
  const message = error?.response?.data?.error?.message

  const codeMap = {
    authentication_required: 'Tu sesión ha expirado. Vuelve a iniciar sesión.',
    invalid_credentials: 'Correo o contraseña incorrectos.',
    email_already_taken: 'Ese correo ya está registrado.',
    invalid_refresh_token: 'Tu sesión ha expirado. Vuelve a iniciar sesión.',
    refresh_token_reuse_detected: 'Tu sesión ha expirado. Vuelve a iniciar sesión.',
    validation_error: 'Revisa los datos e inténtalo de nuevo.',
    resource_in_use: 'No se puede completar esta acción porque el recurso tiene registros asociados.',
  }

  const messageMap = {
    'Initial balance must be zero or greater.': 'El saldo inicial debe ser cero o mayor.',
    'Amount must be greater than zero.': 'El monto debe ser mayor que cero.',
    'Category type must match transaction type.':
      'La categoría debe coincidir con el tipo del movimiento.',
    'Category type must match recurring transaction type.':
      'La categoría debe coincidir con el tipo de la regla.',
    'Start date is required.': 'La fecha de inicio es obligatoria.',
    'End date cannot be earlier than start date.':
      'La fecha de fin no puede ser anterior a la fecha de inicio.',
    'This category type cannot be changed while it is in use.':
      'No se puede cambiar el tipo de la categoría porque ya tiene movimientos asociados.',
    'Account has transactions.': 'No se puede eliminar la cuenta porque tiene movimientos asociados.',
    'Account has recurring transactions.':
      'No se puede eliminar la cuenta porque tiene reglas recurrentes asociadas.',
    'Category has transactions.': 'No se puede eliminar la categoría porque tiene movimientos asociados.',
    'Category has recurring transactions.':
      'No se puede eliminar la categoría porque tiene reglas recurrentes asociadas.',
    'Transaction date is required.': 'La fecha del movimiento es obligatoria.',
  }

  return codeMap[code] || messageMap[message] || message || error?.message || fallback
}
