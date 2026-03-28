/* UPDATE THESE VALUES TO MATCH YOUR SETUP */
const BASE_DOMAIN = window.location.hostname || "localhost"

let REFRESH_RATE_MS = 2000
let statsIntervalId = null
let refreshRateDebounceId = null
const PROCESSOR_BASE_URL = `http://${BASE_DOMAIN}:8100`
const ANALYZER_BASE_URL = `http://${BASE_DOMAIN}:8110`

const PROCESSING_STATS_API_URL = PROCESSOR_BASE_URL + "/stats"
const ANALYZER_API_URL = {
    stats: ANALYZER_BASE_URL + "/stats",
    energy: ANALYZER_BASE_URL + "/energy-event?index=-1",
    temperature: ANALYZER_BASE_URL + "/temperature-event?index=-1"
}

let latest_analyzer_stats = {}

// This function fetches and updates the general statistics
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

const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerHTML = objectToHTML(result)

// aight, i'll match your freak. one-liner to convert an object to an HTML list. don't @ me
const objectToHTML = (obj) => Object.entries(obj).map(([key, value]) => `<p><strong>${key}:</strong><br>${value}</p>`).join("")

const getLocaleDateStr = () => (new Date()).toLocaleString()

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

const getStats = () => {
    document.getElementById("last-updated-value").innerText = getLocaleDateStr()
    
    makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"))
    makeReq(ANALYZER_API_URL.stats, (result) => updateCodeDiv(result, "analyzer-stats") && (latest_analyzer_stats = result) && getEvents())
}

const getEvents = () => {
    latest_analyzer_stats["num_energy_events"] ? makeReq(ANALYZER_API_URL.energy, (result) => updateCodeDiv(result, "event-energy")) : null
    latest_analyzer_stats["num_temperature_events"] ? makeReq(ANALYZER_API_URL.temperature, (result) => updateCodeDiv(result, "event-temperature")) : null
}

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

const setup = () => {
    if (statsIntervalId) {
        clearInterval(statsIntervalId)
    }

    getStats()
    statsIntervalId = setInterval(() => getStats(), REFRESH_RATE_MS)
}

document.addEventListener("DOMContentLoaded", () => {
    wireRefreshRateControls()
    setup()
})