/**
 * Enterprise Application Formatting Utilities
 * Handles all standard localization for currency, dates, and metrics.
 */

/**
 * Format a number into Indian Rupees (INR)
 * @param {number} amount - The numeric value to format
 * @returns {string} - e.g., '₹ 1,50,000'
 */
export const formatCurrency = (amount) => {
  if (isNaN(amount) || amount === null) return '₹0';
  
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(amount);
};

/**
 * Format an ISO date string into a localized readable format
 * @param {string} isoString - e.g., '2026-08-07T12:00:00Z'
 * @returns {string} - e.g., 'Aug 07, 2026'
 */
export const formatDate = (isoString) => {
  if (!isoString) return 'N/A';
  
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  }).format(date);
};

/**
 * Format distance correctly appending 'km'
 * @param {number} distanceInKm 
 * @returns {string} - e.g., '12 km'
 */
export const formatDistance = (distanceInKm) => {
  if (isNaN(distanceInKm) || distanceInKm === null) return 'Unknown distance';
  return `${Number(distanceInKm).toFixed(1)} km`;
};

/**
 * Format weight in quintals or metric tons
 * @param {number} kg - Weight in kilograms
 * @returns {string} - e.g., '50 Quintals'
 */
export const formatWeight = (kg) => {
  if (isNaN(kg) || kg === null) return '0 kg';
  if (kg >= 1000) return `${(kg / 1000).toFixed(1)} MT`; // Metric Tons
  if (kg >= 100) return `${(kg / 100).toFixed(1)} Quintals`;
  return `${kg} kg`;
};
