/**
 * Date utility functions that support application reference date.
 * 
 * This module provides date functions that can use a reference date
 * from the backend API instead of the system date. This is useful when
 * the system date is changed but the application should continue using
 * the original current date.
 */

let cachedApplicationDate = null;
let lastFetchTime = null;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Fetch the application date from the backend API.
 * Results are cached for 5 minutes to avoid excessive API calls.
 * 
 * @returns {Promise<Date|null>} The application date or null if unavailable
 */
async function fetchApplicationDate() {
  const now = Date.now();
  
  // Return cached date if still valid
  if (cachedApplicationDate && lastFetchTime && (now - lastFetchTime) < CACHE_DURATION) {
    return cachedApplicationDate;
  }
  
  try {
    const { systemAPI } = await import('../services/api.js');
    const response = await systemAPI.getApplicationDate();
    const data = response.data;
    
    if (data && data.application_datetime) {
      cachedApplicationDate = new Date(data.application_datetime);
      lastFetchTime = now;
      return cachedApplicationDate;
    }
  } catch (error) {
    console.warn('Failed to fetch application date from API, using system date:', error);
  }
  
  return null;
}

/**
 * Get the current date/time that the application should use.
 * If a reference date is configured on the backend, it will be used.
 * Otherwise, the system date is used.
 * 
 * @returns {Promise<Date>} Current date/time for the application
 */
export async function getApplicationDate() {
  const appDate = await fetchApplicationDate();
  return appDate || new Date();
}

/**
 * Get the current date (date only, no time) that the application should use.
 * 
 * @returns {Promise<Date>} Current date for the application (time set to 00:00:00)
 */
export async function getApplicationToday() {
  const appDate = await getApplicationDate();
  const today = new Date(appDate);
  today.setHours(0, 0, 0, 0);
  return today;
}

/**
 * Synchronous version that uses cached date or falls back to system date.
 * Use this for immediate date comparisons when you can't await.
 * 
 * @returns {Date} Current date/time (may be cached or system date)
 */
export function getApplicationDateSync() {
  if (cachedApplicationDate) {
    return new Date(cachedApplicationDate);
  }
  return new Date();
}

/**
 * Synchronous version for getting today's date.
 * 
 * @returns {Date} Today's date (time set to 00:00:00)
 */
export function getApplicationTodaySync() {
  const today = getApplicationDateSync();
  today.setHours(0, 0, 0, 0);
  return today;
}

/**
 * Clear the cached application date.
 * Call this if you need to force a refresh of the application date.
 */
export function clearDateCache() {
  cachedApplicationDate = null;
  lastFetchTime = null;
}

/**
 * Check if two dates are the same day (ignoring time).
 * 
 * @param {Date} date1 - First date
 * @param {Date} date2 - Second date
 * @returns {boolean} True if dates are on the same day
 */
export function isSameDay(date1, date2) {
  const d1 = new Date(date1);
  const d2 = new Date(date2);
  d1.setHours(0, 0, 0, 0);
  d2.setHours(0, 0, 0, 0);
  return d1.getTime() === d2.getTime();
}

/**
 * Check if a date is today (using application date).
 * 
 * @param {Date|string} date - Date to check
 * @returns {Promise<boolean>} True if the date is today
 */
export async function isToday(date) {
  const today = await getApplicationToday();
  const checkDate = new Date(date);
  checkDate.setHours(0, 0, 0, 0);
  return checkDate.getTime() === today.getTime();
}

/**
 * Synchronous version of isToday.
 * 
 * @param {Date|string} date - Date to check
 * @returns {boolean} True if the date is today
 */
export function isTodaySync(date) {
  const today = getApplicationTodaySync();
  const checkDate = new Date(date);
  checkDate.setHours(0, 0, 0, 0);
  return checkDate.getTime() === today.getTime();
}

/**
 * Format a date for display, comparing it to today.
 * Returns "Today", "Tomorrow", "Yesterday", or formatted date string.
 * 
 * @param {Date|string} date - Date to format
 * @param {Object} options - Formatting options
 * @returns {Promise<string>} Formatted date string
 */
export async function formatDateRelative(date, options = {}) {
  const today = await getApplicationToday();
  const checkDate = new Date(date);
  checkDate.setHours(0, 0, 0, 0);
  
  const diffDays = Math.round((checkDate - today) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) {
    return options.todayLabel || 'Today';
  } else if (diffDays === 1) {
    return options.tomorrowLabel || 'Tomorrow';
  } else if (diffDays === -1) {
    return options.yesterdayLabel || 'Yesterday';
  }
  
  // Format date
  const locale = options.locale || 'en-GB';
  const dateOptions = options.dateOptions || {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  };
  
  return checkDate.toLocaleDateString(locale, dateOptions);
}

