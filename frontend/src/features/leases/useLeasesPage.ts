import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../app/AuthContext";
import {
  ApiError,
  createApiClient,
  type CreateLeaseInput,
  type Lease,
  type Property,
  UnauthorizedApiError,
} from "../../lib/api";
import { getRuntimeConfig } from "../../lib/config";

type LeasesPageState = {
  createLease: (input: CreateLeaseInput) => Promise<void>;
  error: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  leases: Lease[];
  properties: Property[];
};

export function useLeasesPageState(): LeasesPageState {
  const auth = useAuth();
  const navigate = useNavigate();
  const [leases, setLeases] = useState<Lease[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPageData() {
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
        const [leasesResponse, propertiesResponse] = await Promise.all([
          client.listLeases(),
          client.listProperties(),
        ]);
        if (!cancelled) {
          setLeases(leasesResponse.items);
          setProperties(propertiesResponse.items);
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
          errorValue instanceof ApiError ? errorValue.message : "Could not load leases."
        );
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadPageData();

    return () => {
      cancelled = true;
    };
  }, [auth.markSessionExpired, auth.session, navigate]);

  async function createLease(input: CreateLeaseInput) {
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
      const created = await client.createLease(input);
      setLeases((current) => [created, ...current]);
    } catch (errorValue) {
      if (errorValue instanceof UnauthorizedApiError) {
        navigate("/", { replace: true });
        return;
      }
      setError(
        errorValue instanceof ApiError ? errorValue.message : "Could not create the lease."
      );
      throw errorValue;
    } finally {
      setIsSubmitting(false);
    }
  }

  return {
    createLease,
    error,
    isLoading,
    isSubmitting,
    leases,
    properties,
  };
}
