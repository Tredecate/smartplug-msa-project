// This file largely provided by course material.
// Don't judge me for the spaghetti.
const BASE_DOMAIN = window.location.hostname || "localhost"

// ####################
// ###### CONFIG ######
// ####################

// INTERVALS
let REFRESH_RATE_MS = 2000
let HEALTHCHECK_INTERVAL_MS = 5000

// BASE URLS
const HEALTHCHECKER_BASE_URL = `http://${BASE_DOMAIN}:80/healthcheck`
const PROCESSOR_BASE_URL = `http://${BASE_DOMAIN}:80/processor`
const ANALYZER_BASE_URL = `http://${BASE_DOMAIN}:80/analyzer`

// API ENDPOINTS
const HEALTHCHECKER_API_URL = HEALTHCHECKER_BASE_URL + "/status"
const PROCESSING_STATS_API_URL = PROCESSOR_BASE_URL + "/stats"
const ANALYZER_API_URL = {
    stats: ANALYZER_BASE_URL + "/stats",
    energy: ANALYZER_BASE_URL + "/energy-event?index=-1",
    temperature: ANALYZER_BASE_URL + "/temperature-event?index=-1"
}

// ########################
// ###### END CONFIG ######
// ########################

let statsIntervalId = null
let healthIntervalId = null
let refreshRateDebounceId = null
let latest_analyzer_stats = {}

// This function fetches the latest stats from the processor and analyzer and updates the corresponding divs
const getStats = () => {
    document.getElementById("last-updated-value").innerText = getLocaleDateStr()
    
    makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"))
    makeReq(ANALYZER_API_URL.stats, (result) => updateCodeDiv(result, "analyzer-stats") && (latest_analyzer_stats = result) && getEvents())
}

// This function fetches the most recent events from the analyzer (from the kafka topic) and updates the corresponding divs
const getEvents = () => {
    latest_analyzer_stats["num_energy_events"] ? makeReq(ANALYZER_API_URL.energy, (result) => updateCodeDiv(result, "event-energy")) : null
    latest_analyzer_stats["num_temperature_events"] ? makeReq(ANALYZER_API_URL.temperature, (result) => updateCodeDiv(result, "event-temperature")) : null
}

// This function fetches the health status of the services and updates the corresponding div
const getHealth = () => {
    makeReq(HEALTHCHECKER_API_URL, (result) => {
        updateCodeDiv(result["health_statuses"], "healthcheck-stats")
        document.getElementById("health-updated-value").innerText = result["last_update"] ? (new Date(result["last_update"])).toLocaleString() : "N/A"
    })
}

// This function makes a GET request to the provided URL
const makeReq = (url, cb) => {
    fetch(url)
        .then(res => res.json())
        .then((result) => {
            console.log("Received data: ", result)
            cb(result);
        }).catch((error) => {
            if (error)
            updateErrorMessages(error.message)
        })
}

// This function updates the target div with the provided content
const updateCodeDiv = (result, elemId) => {
    const targetElem = document.getElementById(elemId)
    const htmlFromObject = objectToHTML(result)

    if (targetElem.innerHTML == htmlFromObject) {
        return htmlFromObject
    }
    
    return document.getElementById(elemId).innerHTML = objectToHTML(result)
}

// aight, i'll match your freak, mr. instructor. one-liner to convert an object to an HTML list. don't @ me
const objectToHTML = (obj) => Object.entries(obj).map(([key, value]) => `<p><strong>${key}:</strong><br>${value}</p>`).join("")

// This function returns the current date and time in a locale-specific string format
const getLocaleDateStr = () => (new Date()).toLocaleString()

// This function updates the stat polling refresh rate based on user input
const updateRefreshRate = () => {
    const refreshInput = document.getElementById("refresh-rate-ms")
    if (!refreshInput) {
        return
    }

    const nextRate = Number.parseInt(refreshInput.value, 10)
    if (!Number.isFinite(nextRate) || nextRate < 250) {
        updateErrorMessages("Refresh rate must be a number above 250 in milliseconds.")
        refreshInput.value = String(REFRESH_RATE_MS)
        return
    }

    REFRESH_RATE_MS = nextRate
    setup()
}

// This function creates an ephemeral error message div that disappears after 5 seconds
const updateErrorMessages = (message) => {
    const id = Date.now()
    console.log("Creation", id)
    let msg = document.createElement("div")
    msg.id = `error-${id}`
    msg.innerHTML = `<p>Something happened at ${getLocaleDateStr()}!</p><code>${message}</code>`
    document.getElementById("messages").style.display = "block"
    document.getElementById("messages").prepend(msg)
    setTimeout(() => {
        const elem = document.getElementById(`error-${id}`)
        if (elem) { elem.remove() }
    }, 5000)
}

// This function wires up the refresh rate input to allow the user to change the stat polling refresh rate
const wireRefreshRateControls = () => {
    const refreshInput = document.getElementById("refresh-rate-ms")

    if (!refreshInput) {
        return
    }

    refreshInput.value = String(REFRESH_RATE_MS)
    refreshInput.addEventListener("input", () => {
        if (refreshRateDebounceId) {
            clearTimeout(refreshRateDebounceId)
        }

        refreshRateDebounceId = setTimeout(() => {
            updateRefreshRate()
            refreshRateDebounceId = null
        }, 1000)
    })
}

// This function sets up the initial stat and health polling intervals
const setup = () => {
    if (statsIntervalId) {
        clearInterval(statsIntervalId)
    }

    if (healthIntervalId) {
        clearInterval(healthIntervalId)
    }

    // Stats update
    getStats()
    statsIntervalId = setInterval(() => getStats(), REFRESH_RATE_MS)

    // Healthcheck update
    getHealth()
    healthIntervalId = setInterval(() => getHealth(), HEALTHCHECK_INTERVAL_MS)
}

// On your page load, get set, go!
document.addEventListener("DOMContentLoaded", () => {
    wireRefreshRateControls()
    setup()
})