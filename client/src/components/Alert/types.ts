export interface AlertProps {
  type: 'error' | 'success' | 'warning' | 'info';
  message: string;
  onClose?: () => void;
  autoClose?: boolean;
  autoCloseDuration?: number;
}
