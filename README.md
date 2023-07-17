# libtimed
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A python library to interact with the JSON API of [timed](https://github.com/adfinis/timed-backend). It authenticates using a custom OIDC browser flow, locally on your machine.

## Configuration
Your timed OIDC client must allow the following redirect URI for the example to work: `http://localhost:5000/timedctl/auth`

This is work in progress.

## Usage / Examples
There are examples in `./examples`, run them with `poetry run ./examples/<EXAMPLE>.py`. If you have suggestions or additions, please open an issue or a pull request.

## License
Code released under the [GNU Affero General Public License v3.0](LICENSE).
