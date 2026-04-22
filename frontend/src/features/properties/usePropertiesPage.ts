import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/AuthContext";
import {
  ApiError,
  createApiClient,
  type CreatePropertyInput,
  type Property,
  UnauthorizedApiError,
} from "../../lib/api";
import { getRuntimeConfig } from "../../lib/config";

type PropertiesPageState = {
  createProperty: (input: CreatePropertyInput) => Promise<void>;
  error: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  properties: Property[];
};

export function usePropertiesPageState(): PropertiesPageState {
  const auth = useAuth();
  const navigate = useNavigate();
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadProperties() {
      if (!auth.session) {
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        const client = createApiClient({
          config: getRuntimeConfig(),
          onUnauthorized: auth.markSessionExpired,
          session: auth.session,
        });
        const response = await client.listProperties();
        if (!cancelled) {
          setProperties(response.items);
        }
      } catch (errorValue) {
        if (cancelled) {
          return;
        }
        if (errorValue instanceof UnauthorizedApiError) {
          navigate("/", { replace: true });
          return;
        }
        setError(
          errorValue instanceof ApiError
            ? errorValue.message
            : "Could not load properties."
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadProperties();

    return () => {
      cancelled = true;
    };
  }, [auth.markSessionExpired, auth.session, navigate]);

  async function createProperty(input: CreatePropertyInput) {
    if (!auth.session) {
      navigate("/", { replace: true });
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const client = createApiClient({
        config: getRuntimeConfig(),
        onUnauthorized: auth.markSessionExpired,
        session: auth.session,
      });
      const created = await client.createProperty(input);
      setProperties((current) => [created, ...current]);
    } catch (errorValue) {
      if (errorValue instanceof UnauthorizedApiError) {
        navigate("/", { replace: true });
        return;
      }
      setError(
        errorValue instanceof ApiError
          ? errorValue.message
          : "Could not create the property."
      );
      throw errorValue;
    } finally {
      setIsSubmitting(false);
    }
  }

  return {
    createProperty,
    error,
    isLoading,
    isSubmitting,
    properties,
  };
}
