import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { supabase } from "../../lib/supabase";

export function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-baymax-bg px-4">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-baymax-text">
          VEDAMAX
        </h1>
        <p className="mt-2 text-sm text-baymax-textMuted">
          Your personal health companion
        </p>
        <p className="mt-1 text-xs text-baymax-textMuted">
          Educational health information · Not medical advice
        </p>
      </div>

      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-baymax-surface p-8">
        <Auth
          supabaseClient={supabase}
          appearance={{
            theme: ThemeSupa,
            variables: {
              default: {
                colors: {
                  brand: "#5ec8d8",
                  brandAccent: "#4ab8c8",
                  brandButtonText: "#0f1115",
                  defaultButtonBackground: "#1f2329",
                  defaultButtonBackgroundHover: "#2b3038",
                  defaultButtonBorder: "rgba(255,255,255,0.1)",
                  defaultButtonText: "#e8eaed",
                  dividerBackground: "rgba(255,255,255,0.1)",
                  inputBackground: "#0f1115",
                  inputBorder: "rgba(255,255,255,0.1)",
                  inputBorderHover: "#5ec8d8",
                  inputBorderFocus: "#5ec8d8",
                  inputText: "#e8eaed",
                  inputPlaceholder: "#9aa1ab",
                  messageText: "#e8eaed",
                  messageTextDanger: "#e0594a",
                  anchorTextColor: "#5ec8d8",
                  anchorTextHoverColor: "#4ab8c8",
                },
                radii: {
                  borderRadiusButton: "12px",
                  buttonBorderRadius: "12px",
                  inputBorderRadius: "12px",
                },
                space: {
                  inputPadding: "12px 16px",
                  buttonPadding: "12px 16px",
                },
                fonts: {
                  bodyFontFamily: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`,
                  buttonFontFamily: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`,
                  inputFontFamily: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`,
                },
              },
            },
            className: {
              container: "auth-container",
              button: "auth-button",
              input: "auth-input",
            },
          }}
          providers={["google"]}
          redirectTo={window.location.origin}
          socialLayout="horizontal"
          view="sign_in"
          showLinks={true}
          localization={{
            variables: {
              sign_in: {
                email_label: "Email address",
                password_label: "Password",
                button_label: "Sign in",
                social_provider_text: "Continue with {{provider}}",
                link_text: "Don't have an account? Sign up",
              },
              sign_up: {
                email_label: "Email address",
                password_label: "Create a password",
                button_label: "Create account",
                social_provider_text: "Continue with {{provider}}",
                link_text: "Already have an account? Sign in",
              },
              forgotten_password: {
                email_label: "Email address",
                button_label: "Send reset instructions",
                link_text: "Back to sign in",
              },
            },
          }}
        />
      </div>

      <p className="mt-6 text-center text-xs text-baymax-textMuted">
        By signing in, you agree that VEDAMAX provides educational health
        information only and is not a substitute for professional medical advice.
      </p>
    </div>
  );
}
