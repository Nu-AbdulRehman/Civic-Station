import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Changing this value (the current path) clears a caught error, so navigating away from a
   *  broken view recovers without a reload. */
  resetKey?: string;
}

interface State {
  error: Error | null;
}

/** A render-time exception becomes a recoverable state, not a blank page (FR-FE-017). */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("render error", error, info.componentStack);
  }

  componentDidUpdate(previous: Props): void {
    if (this.state.error && previous.resetKey !== this.props.resetKey) this.reset();
  }

  reset = (): void => this.setState({ error: null });

  render(): ReactNode {
    if (!this.state.error) return this.props.children;
    return (
      <div role="alert" className="banner error" data-testid="error-boundary">
        <p>Something went wrong while showing this page.</p>
        <button type="button" onClick={this.reset}>
          Try again
        </button>
      </div>
    );
  }
}
