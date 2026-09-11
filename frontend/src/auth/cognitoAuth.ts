import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
  type CognitoUserSession,
} from 'amazon-cognito-identity-js'

import { config } from '../config'

const userPool = new CognitoUserPool({
  UserPoolId: config.cognitoUserPoolId,
  ClientId: config.cognitoClientId,
})

export function signIn(username: string, pin: string): Promise<CognitoUserSession> {
  const user = new CognitoUser({ Username: username, Pool: userPool })
  const authDetails = new AuthenticationDetails({ Username: username, Password: pin })

  return new Promise((resolve, reject) => {
    user.authenticateUser(authDetails, {
      onSuccess: (session) => resolve(session),
      onFailure: (err: Error) => reject(err),
    })
  })
}

export function signOut(): void {
  userPool.getCurrentUser()?.signOut()
}

export function getCurrentSession(): Promise<CognitoUserSession | null> {
  const user = userPool.getCurrentUser()
  if (!user) return Promise.resolve(null)

  return new Promise((resolve, reject) => {
    user.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err) reject(err)
      else resolve(session)
    })
  })
}
