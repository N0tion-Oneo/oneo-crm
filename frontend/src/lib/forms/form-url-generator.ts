/**
 * Form URL Generator Utility
 * Generates shareable URLs for dynamic forms based on pipeline configuration
 */

export interface FormConfig {
  pipeline_id: string;
  pipeline_slug?: string;
  form_mode: 'internal_full' | 'public_filtered' | 'stage_internal' | 'stage_public';
  stage?: string;
}

export interface FormUrlOptions {
  includeTracking?: boolean;
  expirationHours?: number;
  prefillData?: Record<string, any>;
  utmParams?: {
    source?: string;
    medium?: string;
    campaign?: string;
    term?: string;
    content?: string;
  };
}

/**
 * Generate a form URL based on configuration
 */
export function generateFormUrl(config: FormConfig, options?: FormUrlOptions): string {
  const { pipeline_id, pipeline_slug, form_mode, stage } = config;
  const baseUrl = typeof window !== 'undefined'
    ? window.location.origin
    : process.env.NEXT_PUBLIC_APP_URL || '';

  let path = '/forms';

  switch (form_mode) {
    case 'internal_full':
      path = `/forms/internal/${pipeline_id}`;
      break;
    case 'public_filtered':
      path = `/forms/${pipeline_slug || pipeline_id}`;
      break;
    case 'stage_internal':
      if (!stage) {
        throw new Error('Stage is required for stage_internal form mode');
      }
      // Internal stage forms use query parameter
      path = `/forms/internal/${pipeline_id}`;
      break;
    case 'stage_public':
      if (!stage) {
        throw new Error('Stage is required for stage_public form mode');
      }
      path = `/forms/${pipeline_slug || pipeline_id}/stage/${stage}`;
      break;
    default:
      throw new Error(`Invalid form mode: ${form_mode}`);
  }

  // Build URL with query parameters
  const url = new URL(path, baseUrl);

  // Add stage as query parameter for internal stage forms
  if (form_mode === 'stage_internal' && stage) {
    url.searchParams.set('stage', stage);
  }

  // Add tracking parameters
  if (options?.includeTracking) {
    url.searchParams.set('track', '1');
  }

  // Add expiration if specified
  if (options?.expirationHours && options.expirationHours > 0) {
    const expirationTime = Date.now() + (options.expirationHours * 60 * 60 * 1000);
    url.searchParams.set('expires', expirationTime.toString());
  }

  // Add prefill data as base64 encoded JSON
  if (options?.prefillData && Object.keys(options.prefillData).length > 0) {
    const encodedData = btoa(JSON.stringify(options.prefillData));
    url.searchParams.set('prefill', encodedData);
  }

  // Add UTM parameters for marketing tracking
  if (options?.utmParams) {
    Object.entries(options.utmParams).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(`utm_${key}`, value);
      }
    });
  }

  return url.toString();
}

/**
 * Generate a shareable form link with tracking
 */
export function generateFormShareableLink(
  config: FormConfig,
  options?: FormUrlOptions & { shortLink?: boolean }
): string {
  const fullUrl = generateFormUrl(config, {
    ...options,
    includeTracking: true
  });

  // In production, you might want to create a short link
  // This would require an API call to a URL shortening service
  if (options?.shortLink) {
    // TODO: Implement short link generation
    return fullUrl;
  }

  return fullUrl;
}

/**
 * Parse form URL to extract configuration
 */
export function parseFormUrl(url: string): FormConfig | null {
  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname;

    // Parse internal form (both full and stage)
    if (pathname.match(/^\/forms\/internal\/([^\/]+)$/)) {
      const matches = pathname.match(/^\/forms\/internal\/([^\/]+)$/);
      const stage = urlObj.searchParams.get('stage');

      if (stage) {
        // Internal stage form with query parameter
        return {
          pipeline_id: matches![1],
          form_mode: 'stage_internal',
          stage: stage
        };
      } else {
        // Internal full form
        return {
          pipeline_id: matches![1],
          form_mode: 'internal_full'
        };
      }
    }

    // Parse public form
    if (pathname.match(/^\/forms\/([^\/]+)$/)) {
      const matches = pathname.match(/^\/forms\/([^\/]+)$/);
      return {
        pipeline_id: matches![1],
        pipeline_slug: matches![1],
        form_mode: 'public_filtered'
      };
    }

    // Parse stage public form
    if (pathname.match(/^\/forms\/([^\/]+)\/stage\/([^\/]+)$/)) {
      const matches = pathname.match(/^\/forms\/([^\/]+)\/stage\/([^\/]+)$/);
      return {
        pipeline_id: matches![1],
        pipeline_slug: matches![1],
        form_mode: 'stage_public',
        stage: matches![2]
      };
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Validate if a form URL has expired
 */
export function isFormUrlExpired(url: string): boolean {
  try {
    const urlObj = new URL(url);
    const expires = urlObj.searchParams.get('expires');

    if (!expires) {
      return false; // No expiration set
    }

    const expirationTime = parseInt(expires, 10);
    return Date.now() > expirationTime;
  } catch {
    return false;
  }
}

/**
 * Extract prefill data from form URL
 */
export function extractPrefillData(url: string): Record<string, any> | null {
  try {
    const urlObj = new URL(url);
    const prefillParam = urlObj.searchParams.get('prefill');

    if (!prefillParam) {
      return null;
    }

    const decodedData = atob(prefillParam);
    return JSON.parse(decodedData);
  } catch {
    return null;
  }
}