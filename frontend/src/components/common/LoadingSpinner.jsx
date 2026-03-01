import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingSpinner({ size = 20, className = '' }) {
  return <Loader2 size={size} className={`animate-spin text-brand-600 ${className}`} />;
}
