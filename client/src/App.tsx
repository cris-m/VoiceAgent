import { createBrowserRouter, RouterProvider } from 'react-router';
import { Provider } from 'react-redux';
import { routes } from '@/routes';
import { store } from '@store';
import { VoiceConfigProvider } from '@context/VoiceConfigContext';
import { ErrorBoundary } from '@components/ErrorBoundary';
import { AuthInitializer } from '@components/AuthInitializer';

const router = createBrowserRouter(routes);

function App() {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <AuthInitializer>
          <VoiceConfigProvider>
            <RouterProvider router={router} />
          </VoiceConfigProvider>
        </AuthInitializer>
      </Provider>
    </ErrorBoundary>
  );
}

export default App;
