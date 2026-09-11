function required(name: keyof ImportMetaEnv, value: string): string {
  if (!value) {
    console.warn(`Missing env var ${name} — copy .env.example to .env.local once the backend is deployed.`)
  }
  return value
}

export const config = {
  cognitoUserPoolId: required('VITE_COGNITO_USER_POOL_ID', import.meta.env.VITE_COGNITO_USER_POOL_ID),
  cognitoClientId: required('VITE_COGNITO_CLIENT_ID', import.meta.env.VITE_COGNITO_CLIENT_ID),
  apiBaseUrl: required('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL),
}
