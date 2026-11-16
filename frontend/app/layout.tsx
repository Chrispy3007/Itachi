import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Itachi — Shadow Media Vault',
  description: 'A personal media workspace in the shadows.'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
